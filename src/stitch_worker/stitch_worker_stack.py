from aws_cdk import (
    Stack,
    aws_lambda,
    aws_sqs,
    aws_lambda_event_sources,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_ecr,
    aws_sns_subscriptions,
    Duration,
    Tags,
    aws_sns,
    aws_secretsmanager,
    aws_s3,
    aws_ec2,
)
from constructs import Construct

from stitch_worker.processes_loader import load_processes_config


class StitchWorkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        tags = self.node.try_get_context("tags")
        naming = self.node.try_get_context("naming")
        settings = self.node.try_get_context("settings")
        self.env = self.node.try_get_context("env") or "dev"
        self.prefix = naming["prefix"]
        self.suffix = self.env

        tags.update({"Environment": self.env})
        # Apply tags to all resources in the stack
        for key, value in tags.items():
            Tags.of(self).add(key, value)

        self.repository = aws_ecr.Repository.from_repository_arn(
            self,
            "StitchWorkerRepository",
            repository_arn="arn:aws:ecr:us-east-2:613563724766:repository/stitch-worker",
        )

        self.image_tag = settings["lambda_image_tag"]
        print(f"Using image tag: {self.image_tag}")

        # Create EventBridge Bus
        self.bus = aws_events.EventBus(
            self, "StitchEventBridgeBus", event_bus_name=f"{self.prefix}-{self.suffix}-datastores-bus"
        )

        if settings["create_hub_instance"]:
            ec2_instance = self.create_hub_instance()
            ec2_host = ec2_instance.instance_public_dns_name
            self.create_ec2_state_change_handler(ec2_instance)
        else:
            ec2_host = "localhost"

        default_environment = {
            "DEBUG_MODE": "True",
            "POWERTOOLS_SERVICE_NAME": "stitch_worker",
            "POWERTOOLS_LOG_LEVEL": "INFO",
            "POWERTOOLS_LOG_FORMAT": "JSON",
            "EVENT_BUS_NAME": self.bus.event_bus_name,
            "LOGGER_NAME": "stitch_worker",
            "LOG_LEVEL": "DEBUG",
            "HUB_URL": settings.get("hub_url") or f"http://{ec2_host}:5050/hub/api/v1",
            "SYSTEM_ADMIN_API_KEY": settings.get("system_admin_api_key"),
        }

        if self.env == "local":
            openai_api_key = settings["openai_api_key"]
            pinecone_api_key = settings["pinecone_api_key"]
            pinecone_index_name = settings["pinecone_index_name"]
            database_password = settings["database_password"]
            self.s3_bucket = aws_s3.Bucket(
                self,
                "StitchWorkerS3Bucket",
                bucket_name=f"{self.prefix}-{self.suffix}-files",
            )
        else:
            secret_manager = aws_secretsmanager.Secret.from_secret_name_v2(
                self,
                "WorkerSecret",
                secret_name=f"ayd/{self.env}/worker",
            )
            openai_api_key = secret_manager.secret_value_from_json("OPENAI_API_KEY").to_string()
            pinecone_api_key = secret_manager.secret_value_from_json("PINECONE_API_KEY").to_string()
            pinecone_index_name = secret_manager.secret_value_from_json("PINECONE_INDEX_NAME").to_string()
            database_password = (
                settings["database_password"] or secret_manager.secret_value_from_json("DATABASE_PASSWORD").to_string()
            )
            self.s3_bucket = aws_s3.Bucket.from_bucket_name(
                self,
                "StitchWorkerS3Bucket",
                bucket_name=f"ayd-{self.suffix}-files",
            )

        # Initialize document extraction resources if needed
        document_extraction_topic = None
        document_extraction_role = None

        if settings["lambda_document_extraction"]:
            document_extraction_topic, document_extraction_queue, document_extraction_role = (
                self.create_document_extraction_notification_lambda(default_environment=default_environment)
            )

        # Load processes configuration from YAML
        processes = load_processes_config(
            settings=settings,
            s3_bucket_name=self.s3_bucket.bucket_name,
            document_extraction_topic_arn=document_extraction_topic.topic_arn if document_extraction_topic else None,
            document_extraction_role_arn=document_extraction_role.role_arn if document_extraction_role else None,
            openai_api_key=openai_api_key,
            pinecone_api_key=pinecone_api_key,
            pinecone_index_name=pinecone_index_name,
            ec2_host=ec2_host,
            database_password=database_password,
        )

        # Create SQS queues and Lambda functions for each process
        for process in processes:
            if not process["enabled"]:
                continue

            # Create SQS queue
            queue = aws_sqs.Queue(
                self,
                f"{process['id_prefix']}Queue",
                queue_name=f"{self.prefix}-{self.suffix}-{process['name']}",
                visibility_timeout=Duration.seconds(300),
                retention_period=Duration.days(14),
            )

            # Create Lambda function
            if self.env == "local":
                lambda_fn = aws_lambda.Function(
                    self,
                    f"{process['id_prefix']}Lambda",
                    function_name=f"{self.prefix}-{self.suffix}-{process['name']}",
                    runtime=aws_lambda.Runtime.PYTHON_3_13,
                    handler=f"worker.handlers.{process['module']}.index.handler",
                    code=aws_lambda.Code.from_asset("/Users/jason/Downloads/worker_deployment_package.zip"),
                    timeout=Duration.seconds(300),
                    environment=default_environment | process.get("environment", {}),
                    memory_size=process.get("memory_size", 128),
                    logging_format=aws_lambda.LoggingFormat.JSON,
                )
            else:
                lambda_fn = aws_lambda.DockerImageFunction(
                    self,
                    f"{process['id_prefix']}Lambda",
                    function_name=f"{self.prefix}-{self.suffix}-{process['name']}",
                    code=aws_lambda.DockerImageCode.from_ecr(
                        repository=self.repository,
                        tag_or_digest=self.image_tag,
                        cmd=[f"worker.handlers.{process['module']}.index.handler"],
                    ),
                    logging_format=aws_lambda.LoggingFormat.JSON,
                    timeout=Duration.seconds(300),
                    environment=default_environment | process.get("environment", {}),
                    memory_size=process.get("memory_size", 128),
                )

            # Add EventBridge permissions to Lambda
            lambda_fn.add_to_role_policy(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW, actions=["events:PutEvents"], resources=[self.bus.event_bus_arn]
                )
            )

            if policies := process.get("additional_policies"):
                for policy in policies:
                    lambda_fn.add_to_role_policy(policy)

            # Add SQS event source to Lambda
            lambda_fn.add_event_source(aws_lambda_event_sources.SqsEventSource(queue, batch_size=1))

            # Create EventBridge rule
            if process["event_pattern"]:
                aws_events.Rule(
                    self,
                    id=f"Stitch{process['id_prefix']}EventRule",
                    enabled=True,
                    event_bus=self.bus,
                    rule_name=f"{self.prefix}-{self.suffix}-{process['name']}",
                    event_pattern=aws_events.EventPattern(**process["event_pattern"]),
                    targets=[aws_events_targets.SqsQueue(queue)],
                )

        # Create EventBridge rule for S3 Object Created on default event bus
        aws_events.Rule(
            self,
            "StitchDocumentUploadEventRule",
            enabled=True,
            rule_name=f"{self.prefix}-{self.suffix}-document-upload",
            event_pattern=aws_events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [self.s3_bucket.bucket_name]},
                    "object": {"key": [{"wildcard": "jdtest/*.pdf"}]},
                },
            ),
            targets=[aws_events_targets.EventBus(self.bus)],
        )

    def create_document_extraction_notification_lambda(
        self, default_environment: dict
    ) -> tuple[aws_sns.Topic, aws_sqs.Queue, aws_iam.Role]:
        # Create SNS Topic
        topic = aws_sns.Topic(
            self, "TextExtractionTopic", topic_name=f"AmazonTextract-{self.prefix}-{self.suffix}-text-extraction-topic"
        )

        # Create SQS Queue for SNS Topic
        queue = aws_sqs.Queue(
            self,
            "TextExtractionNotificationQueue",
            queue_name=f"{self.prefix}-{self.suffix}-text-extraction-notification",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14),
        )

        # Add SNS Topic to SQS Queue
        topic.add_subscription(aws_sns_subscriptions.SqsSubscription(queue))

        # Add Lambda Function to SQS Queue
        if self.env == "local":
            lambda_fn = aws_lambda.Function(
                self,
                "DocumentExtractionNotificationLambda",
                function_name=f"{self.prefix}-{self.suffix}-document-extraction-notification",
                runtime=aws_lambda.Runtime.PYTHON_3_13,
                handler="worker.handlers.document_extraction_notification.index.handler",
                code=aws_lambda.Code.from_asset("/Users/jason/Downloads/worker_deployment_package.zip"),
                logging_format=aws_lambda.LoggingFormat.JSON,
                timeout=Duration.seconds(300),
                environment=default_environment
                | {
                    "TEXT_EXTRACTION_S3_BUCKET": self.s3_bucket.bucket_name,
                    "TEXT_EXTRACTION_S3_KEY_PREFIX": "textract-output",
                },
            )
        else:
            lambda_fn = aws_lambda.DockerImageFunction(
                self,
                "DocumentExtractionNotificationLambda",
                function_name=f"{self.prefix}-{self.suffix}-document-extraction-notification",
                code=aws_lambda.DockerImageCode.from_ecr(
                    repository=self.repository,
                    tag_or_digest=self.image_tag,
                    cmd=["worker.handlers.document_extraction_notification.index.handler"],
                ),
                logging_format=aws_lambda.LoggingFormat.JSON,
                timeout=Duration.seconds(300),
                environment=default_environment
                | {
                    "TEXT_EXTRACTION_S3_BUCKET": self.s3_bucket.bucket_name,
                    "TEXT_EXTRACTION_S3_KEY_PREFIX": "textract-output",
                },
            )

        lambda_fn.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW, actions=["events:PutEvents"], resources=[self.bus.event_bus_arn]
            )
        )

        lambda_fn.add_event_source(aws_lambda_event_sources.SqsEventSource(queue))

        # Create IAM Role for Textract to publish to SNS Topic
        role = aws_iam.Role(
            self,
            "TextractSNSRole",
            role_name=f"{self.prefix}-{self.suffix}-textract-sns-role",
            assumed_by=aws_iam.ServicePrincipal("textract.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonTextractServiceRole")
            ],
            description="Role for Textract to publish to SNS Topic",
        )

        return topic, queue, role

    def create_hub_instance(self) -> aws_ec2.Instance:
        """Create EC2 instance for hub"""
        user_data = aws_ec2.UserData.for_linux()
        user_data.add_commands(
            "set -e",
            "echo 'Starting EC2 instance setup...'",
            "",
            "# Update system packages",
            "echo 'Updating system packages...'",
            "sudo yum update -y",
            "",
            "# Install Docker",
            "echo 'Installing Docker...'",
            "sudo yum install docker -y",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
            "sudo usermod -a -G docker ec2-user",
            "",
            "# Install Git",
            "echo 'Installing Git...'",
            "sudo yum install git -y",
            "",
            "# Install Docker Compose",
            "echo 'Installing Docker Compose...'",
            "sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose",
            "sudo chmod +x /usr/local/bin/docker-compose",
            "",
            "# Create Docker network",
            "echo 'Creating Docker network...'",
            "docker network create -d bridge local-test-net || true",
            "",
            "# Keep the commented commands below for reference",
            "# echo 'Cloning repository...'",
            "# git clone https://github.com/askyourpolicy/ayp-hub.git",
            "# cd ayp-hub",
            "# git checkout feat/dockerize",
            "# docker build -t hub .",
            "",
            "echo 'EC2 instance setup completed successfully!'",
        )

        vpc = aws_ec2.Vpc.from_lookup(self, "AypDevVpc", vpc_id="vpc-006d3d536785de977")
        security_group = aws_ec2.SecurityGroup(self, "StitchHubSecurityGroup", vpc=vpc, allow_all_outbound=True)
        security_group.add_ingress_rule(
            peer=aws_ec2.Peer.any_ipv4(), connection=aws_ec2.Port.tcp(port=5050), description="allow access to hub"
        )

        ec2_instance = aws_ec2.Instance(
            self,
            "StitchHubInstance",
            instance_type=aws_ec2.InstanceType("t2.micro"),
            instance_name=f"{self.prefix}-{self.suffix}-hub-instance",
            machine_image=aws_ec2.MachineImage.latest_amazon_linux2(),
            user_data=user_data,
            vpc=vpc,
            associate_public_ip_address=True,
            require_imdsv2=True,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC),
            block_devices=[
                aws_ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=aws_ec2.BlockDeviceVolume.ebs(volume_size=10),
                )
            ],
            security_group=security_group,
            role=aws_iam.Role.from_role_arn(
                self,
                "AypDevBastionInstanceRole",
                role_arn="arn:aws:iam::613563724766:role/ayp-dev-bastion-instance-role",
            ),
        )

        return ec2_instance

    def create_ec2_state_change_handler(self, ec2_instance: aws_ec2.Instance):
        """Create EventBridge rule and Lambda to update environment variables when EC2 IP changes"""
        # Create Lambda function to handle EC2 state changes
        state_change_handler = aws_lambda.Function(
            self,
            "EC2StateChangeHandler",
            function_name=f"{self.prefix}-{self.suffix}-ec2-state-change-handler",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=aws_lambda.Code.from_asset(
                path="src/stitch_worker/handlers/ec2_state_changer",
                # bundling=aws_lambda.BundlingOptions(
                #     image=aws_lambda.Runtime.PYTHON_3_13.bundling_image,
                #     command=["bash", "-c", "pip install -r requirements.txt && cp -r * /asset-output/"]
                # )
            ),
            logging_format=aws_lambda.LoggingFormat.JSON,
            timeout=Duration.seconds(300),
            environment={
                "POWERTOOLS_SERVICE_NAME": "ec2_state_change_handler",
                "POWERTOOLS_LOG_LEVEL": "INFO",
                "PREFIX": self.prefix,
                "SUFFIX": self.suffix,
                "EC2_INSTANCE_ID": ec2_instance.instance_id,
            },
        )

        # Grant permissions to the state change handler
        state_change_handler.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstances",
                    "lambda:GetFunctionConfiguration",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:ListFunctions",
                ],
                resources=["*"],
            )
        )

        # Create EventBridge rule to detect EC2 instance state changes
        aws_events.Rule(
            self,
            "EC2StateChangeRule",
            rule_name=f"{self.prefix}-{self.suffix}-ec2-state-change-rule",
            event_pattern=aws_events.EventPattern(
                source=["aws.ec2"],
                detail_type=["EC2 Instance State-change Notification"],
                detail={"state": ["running"], "instance-id": [ec2_instance.instance_id]},
            ),
            targets=[aws_events_targets.LambdaFunction(state_change_handler)],
        )

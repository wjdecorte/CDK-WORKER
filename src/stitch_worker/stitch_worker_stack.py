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
)
from constructs import Construct

from stitch_worker.enums import EventType


class StitchWorkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        tags = self.node.try_get_context("tags")
        naming = self.node.try_get_context("naming")
        settings = self.node.try_get_context("settings")
        self.prefix = naming["prefix"]
        self.suffix = naming["suffix"]

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

        if settings["lambda_document_extraction"]:
            document_extraction_topic, document_extraction_queue, document_extraction_role = (
                self.create_document_extraction_notification_lambda()
            )

        # Define process names
        processes = [
            {
                "name": "document-extract",
                "enabled": settings["lambda_document_extraction"],
                "module": "document_extract",
                "event_pattern": {
                    "source": ["aws.s3"],
                    "detail_type": [EventType.S3_OBJECT_CREATED],
                    "detail": {"bucket": {"name": ["ayd-dev-files"]}},
                },
                "id_prefix": "DocumentExtract",
                "additional_policies": [
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["s3:Get*", "s3:List*", "s3:Put*"],
                        resources=["*"],
                    ),
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["textract:StartDocumentAnalysis"],
                        resources=["*"],
                    ),
                ],
                "environment": {
                    "TEXT_EXTRACTION_S3_BUCKET": "ayd-dev-files",
                    "TEXT_EXTRACTION_S3_KEY_PREFIX": "textract-output",
                    "TEXT_EXTRACTION_SNS_TOPIC_ARN": document_extraction_topic.topic_arn,
                    "TEXT_EXTRACTION_SNS_ROLE_ARN": document_extraction_role.role_arn,
                },
            },
            {
                "name": "block-standardization",
                "enabled": settings["lambda_block_standardization"],
                "module": "block_standardization",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.DOCUMENT_EXTRACTION_COMPLETED],
                },
                "id_prefix": "BlockProcessing",
                "additional_policies": [
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["s3:Get*", "s3:List*", "s3:Put*"],
                        resources=["*"],
                    ),
                ],
                "environment": {
                    "BLOCK_SKIP_KEY_VALUE_SET": "False",
                },
            },
            {
                "name": "block-summarization",
                "enabled": settings["lambda_block_summarization"],
                "module": "block_summarization",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_STANDARDIZATION_COMPLETED],
                },
                "id_prefix": "BlockSummarization",
                "additional_policies": [
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["s3:Get*", "s3:List*", "s3:Put*"],
                        resources=["*"],
                    ),
                ],
                "environment": {
                    "OPENAI_API_KEY": aws_secretsmanager.Secret.from_secret_name_v2(
                        self,
                        "WorkerSecret",
                        secret_name="ayd/dev/worker",
                    )
                    .secret_value_from_json("OPENAI_API_KEY")
                    .to_string(),
                },
            },
            {
                "name": "block-refinement",
                "enabled": settings["lambda_block_refinement"],
                "module": "block_refinement",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_SUMMARIZATION_COMPLETED],
                },
                "id_prefix": "BlockRefinement",
                "additional_policies": [
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["s3:Get*", "s3:List*", "s3:Put*"],
                        resources=["*"],
                    ),
                ],
                "environment": {
                    "OPENAI_API_KEY": aws_secretsmanager.Secret.from_secret_name_v2(
                        self,
                        "WorkerSecretOpenAI",
                        secret_name="ayd/dev/worker",
                    )
                    .secret_value_from_json("OPENAI_API_KEY")
                    .to_string(),
                    "PINECONE_API_KEY": aws_secretsmanager.Secret.from_secret_name_v2(
                        self,
                        "WorkerSecretPinecone",
                        secret_name="ayd/dev/worker",
                    )
                    .secret_value_from_json("PINECONE_API_KEY")
                    .to_string(),
                    "PINECONE_INDEX_NAME": "ayd-cosine-staging",
                },
            },
            {
                "name": "document-summary",
                "enabled": settings["lambda_document_summary"],
                "module": "document_summary",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_STANDARDIZATION_COMPLETED],
                },
                "id_prefix": "DocumentSummary",
                "additional_policies": [],
            },
            {
                "name": "seed-questions",
                "enabled": settings["lambda_seed_questions"],
                "module": "seed_questions",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_STANDARDIZATION_COMPLETED],
                    "detail": {
                        "metadata": {
                            "seed_questions_list": [{"exists": True}],
                        }
                    },
                },
                "id_prefix": "SeedQuestions",
                "additional_policies": [],
            },
            {
                "name": "feature-extraction",
                "enabled": settings["lambda_feature_extraction"],
                "module": "feature_extraction",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_STANDARDIZATION_COMPLETED],
                    "detail": {
                        "metadata": {
                            "feature_types": [{"exists": True}],
                        }
                    },
                },
                "id_prefix": "FeatureExtraction",
                "additional_policies": [],
            },
            {
                "name": "split-file",
                "enabled": settings["lambda_split_file"],
                "module": "split_file",
                "event_pattern": {
                    "source": ["aws.s3"],
                    "detail_type": [EventType.S3_OBJECT_CREATED],
                    "detail": {"bucket": {"name": ["ayd-dev-files"]}},
                },
                "id_prefix": "SplitFile",
                "additional_policies": [
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["s3:Get*", "s3:List*", "s3:Put*"],
                        resources=["*"],
                    ),
                ],
                "memory_size": 2048,
            },
        ]

        default_environment = {
            "DEBUG_MODE": "True",
            "POWERTOOLS_SERVICE_NAME": "stitch_worker",
            "POWERTOOLS_LOG_LEVEL": "INFO",
            "POWERTOOLS_LOG_FORMAT": "JSON",
            "EVENT_BUS_NAME": self.bus.event_bus_name,
            "LOGGER_NAME": "stitch_worker",
            "LOG_LEVEL": "DEBUG",
        }
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
                detail_type=[EventType.S3_OBJECT_CREATED],
                detail={
                    "bucket": {"name": ["ayd-dev-files"]},
                    "object": {"key": [{"wildcard": "jdtest/*.pdf"}]},
                },
            ),
            targets=[aws_events_targets.EventBus(self.bus)],
        )

    def create_document_extraction_notification_lambda(self):
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
            environment={
                "DEBUG_MODE": "True",
                "POWERTOOLS_SERVICE_NAME": "stitch_worker",
                "POWERTOOLS_LOG_LEVEL": "INFO",
                "POWERTOOLS_LOG_FORMAT": "JSON",
                "EVENT_BUS_NAME": self.bus.event_bus_name,
                "LOGGER_NAME": "stitch_worker",
                "LOG_LEVEL": "DEBUG",
                "TEXT_EXTRACTION_S3_BUCKET": "ayd-dev-files",
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


class StitchOrchestrationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        naming = self.node.try_get_context("naming")
        prefix = naming["prefix"]
        suffix = naming["suffix"]

        # Create SQS queue
        queue = aws_sqs.Queue(
            self,
            "StitchOrchestrationQueue",
            queue_name=f"{prefix}-{suffix}-start-orchestration",
        )

        # Create EventBridge Bus
        bus = aws_events.EventBus(self, "StitchOrchestrationBus", event_bus_name=f"{prefix}-{suffix}-orchestrations")

        # Create EventBridge rule for S3 Object Created on default event bus
        aws_events.Rule(
            self,
            "StitchOrchestrationRule",
            event_bus=bus,
            enabled=True,
            rule_name=f"{prefix}-{suffix}-start-orchestration",
            event_pattern=aws_events.EventPattern(source=["stitch.orchestration"], detail_type=["StartOrchestration"]),
            targets=[aws_events_targets.SqsQueue(queue)],
        )

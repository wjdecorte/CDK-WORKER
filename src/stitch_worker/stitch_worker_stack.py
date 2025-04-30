from aws_cdk import (
    Stack,
    aws_lambda,
    aws_sqs,
    aws_lambda_event_sources,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_ecr,
    Duration,
    Tags,
    aws_sns,
)
from constructs import Construct

from stitch_worker.enums import EventType


class StitchWorkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        tags = self.node.try_get_context("tags")
        naming = self.node.try_get_context("naming")
        prefix = naming["prefix"]
        suffix = naming["suffix"]

        # Apply tags to all resources in the stack
        for key, value in tags.items():
            Tags.of(self).add(key, value)

        # Create EventBridge Bus
        bus = aws_events.EventBus(self, "StitchEventBridgeBus", event_bus_name=f"{prefix}-{suffix}-datastores-bus")

        # Create SNS Topic
        topic = aws_sns.Topic(
            self, "TextExtractionTopic", topic_name=f"AmazonTextract-{prefix}-{suffix}-text-extraction-topic"
        )

        # Define process names
        processes = [
            {
                "name": "document-extract",
                "module": "document_extract",
                "event_pattern": {
                    "source": ["aws.s3"],
                    "detail_type": [EventType.S3_OBJECT_CREATED],
                    "detail": {"bucket": {"name": ["ayd-dev-files"]}},
                },
                "id_prefix": "DocumentExtract",
            },
            {
                "name": "block-processing",
                "module": "block_processing",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.DOCUMENT_EXTRACTION_COMPLETED],
                },
                "id_prefix": "BlockProcessing",
            },
            {
                "name": "document-summary",
                "module": "document_summary",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                },
                "id_prefix": "DocumentSummary",
            },
            {
                "name": "seed-questions",
                "module": "seed_questions",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                    "detail": {
                        "metadata": {
                            "seed_questions_list": [{"exists": True}],
                        }
                    },
                },
                "id_prefix": "SeedQuestions",
            },
            {
                "name": "feature-extraction",
                "module": "feature_extraction",
                "event_pattern": {
                    "source": ["stitch.worker"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                    "detail": {
                        "metadata": {
                            "feature_types": [{"exists": True}],
                        }
                    },
                },
                "id_prefix": "FeatureExtraction",
            },
        ]

        repository = aws_ecr.Repository.from_repository_arn(
            self,
            "StitchWorkerRepository",
            repository_arn="arn:aws:ecr:us-east-2:613563724766:repository/stitch-worker",
        )

        image_tag = "0.1.4"

        # Create SQS queues and Lambda functions for each process
        for process in processes:
            # Create SQS queue
            queue = aws_sqs.Queue(
                self,
                f"{process['id_prefix']}Queue",
                queue_name=f"{prefix}-{suffix}-{process['name']}",
                visibility_timeout=Duration.seconds(300),
                retention_period=Duration.days(14),
            )

            # Create Lambda function
            lambda_fn = aws_lambda.DockerImageFunction(
                self,
                f"{process['id_prefix']}Lambda",
                function_name=f"{prefix}-{suffix}-{process['name']}",
                code=aws_lambda.DockerImageCode.from_ecr(
                    repository=repository,
                    tag_or_digest=image_tag,
                    cmd=[f"stitch_worker.handlers.{process['module']}.index.handler"],
                ),
                timeout=Duration.seconds(300),
                environment={
                    "DEBUG_MODE": "True",
                    "POWERTOOLS_SERVICE_NAME": "stitch_worker",
                    "POWERTOOLS_LOG_LEVEL": "DEBUG",
                    "POWERTOOLS_LOG_FORMAT": "JSON",
                    "EVENT_BUS_NAME": bus.event_bus_name,
                    "LOGGER_NAME": "stitch_worker",
                    "LOG_LEVEL": "DEBUG",
                    "TEXT_EXTRACTION_SNS_TOPIC_ARN": topic.topic_arn,
                    "TEXT_EXTRACTION_SNS_ROLE_ARN": "arn:aws:iam::aws:policy/service-role/AmazonTextractServiceRole",
                    "TEXT_EXTRACTION_S3_BUCKET": "ayd-dev-files",
                    "TEXT_EXTRACTION_S3_KEY_PREFIX": "textract-output",
                },
            )

            # Add EventBridge permissions to Lambda
            lambda_fn.add_to_role_policy(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW, actions=["events:PutEvents"], resources=[bus.event_bus_arn]
                )
            )

            # Add SQS event source to Lambda
            lambda_fn.add_event_source(aws_lambda_event_sources.SqsEventSource(queue))

            # Create EventBridge rule
            aws_events.Rule(
                self,
                id=f"Stitch{process['id_prefix']}EventRule",
                enabled=True,
                event_bus=bus,
                rule_name=f"{prefix}-{suffix}-{process['name']}",
                event_pattern=aws_events.EventPattern(**process["event_pattern"]),
                targets=[aws_events_targets.SqsQueue(queue)],
            )

        # Create EventBridge rule for S3 Object Created on default event bus
        aws_events.Rule(
            self,
            "StitchDocumentUploadEventRule",
            enabled=True,
            rule_name=f"{prefix}-{suffix}-document-upload",
            event_pattern=aws_events.EventPattern(
                source=["aws.s3"],
                detail_type=[EventType.S3_OBJECT_CREATED],
                detail={
                    "bucket": {"name": ["ayd-dev-files"]},
                    "object": {"key": [{"prefix": "jdtest/"}, {"suffix": ".pdf"}]},
                },
            ),
            targets=[aws_events_targets.EventBus(bus)],
        )


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

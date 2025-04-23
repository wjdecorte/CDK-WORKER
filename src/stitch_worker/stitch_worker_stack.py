from aws_cdk import (
    Stack,
    aws_lambda,
    aws_sqs,
    aws_lambda_event_sources,
    aws_events,
    aws_events_targets,
    aws_iam,
    Duration,
    Tags,
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
        bus = aws_events.EventBus(self, "StitchEventBridgeBus", event_bus_name=f"{prefix}-event-bus-{suffix}")

        # Define process names

        processes = [
            {
                "name": "document-extract",
                "module": "document_extract",
                "event_pattern": {
                    "source": ["aws.s3"],
                    "detail_type": ["Object Created"],
                    "detail": {"bucket": {"name": ["ayd-dev-files"]}},
                },
                "id_prefix": "DocumentExtract",
            },
            {
                "name": "block-processing",
                "module": "block_processing",
                "event_pattern": {
                    "source": ["stitch.worker.document_extract"],
                    "detail_type": [EventType.DOCUMENT_EXTRACTION_COMPLETED],
                },
                "id_prefix": "BlockProcessing",
            },
            {
                "name": "document-summary",
                "module": "document_summary",
                "event_pattern": {
                    "source": ["stitch.worker.block_processing"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                    "detail": {
                        "metadata": {
                            "document_summary": True,
                        }
                    },
                },
                "id_prefix": "DocumentSummary",
            },
            {
                "name": "seed-questions",
                "module": "seed_questions",
                "event_pattern": {
                    "source": ["stitch.worker.block_processing"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                    "detail": {
                        "metadata": {
                            "seed_questions_list": [{"question": "What is the name of the person in the document?"}],
                        }
                    },
                },
                "id_prefix": "SeedQuestions",
            },
            {
                "name": "feature-extraction",
                "module": "feature_extraction",
                "event_pattern": {
                    "source": ["stitch.worker.block_processing"],
                    "detail_type": [EventType.BLOCK_PROCESSING_COMPLETED],
                    "detail": {
                        "metadata": {
                            "feature_types": [
                                "text_features",
                                "table_features",
                                "image_features",
                            ],
                        }
                    },
                },
                "id_prefix": "FeatureExtraction",
            },
        ]

        # Create SQS queues and Lambda functions for each process
        for process in processes:
            # Create SQS queue
            queue = aws_sqs.Queue(
                self,
                f"{process['id_prefix']}Queue",
                queue_name=f"{prefix}-{process['name']}-queue-{suffix}",
                visibility_timeout=Duration.seconds(300),
                retention_period=Duration.days(14),
            )

            # Create Lambda function
            lambda_fn = aws_lambda.Function(
                self,
                f"{process['id_prefix']}Lambda",
                function_name=f"{prefix}-{process['name']}-lambda-{suffix}",
                runtime=aws_lambda.Runtime.PYTHON_3_12,
                handler="index.handler",
                code=aws_lambda.Code.from_asset(f"src/stitch_worker/lambda/{process['module']}"),
                timeout=Duration.seconds(300),
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
                rule_name=f"{prefix}-{process['name']}-event-rule-{suffix}",
                event_pattern=aws_events.EventPattern(**process["event_pattern"]),
                targets=[aws_events_targets.SqsQueue(queue)],
            )

        # Create EventBridge rule for S3 Object Created on default event bus
        aws_events.Rule(
            self,
            "StitchDocumentUploadEventRule",
            enabled=True,
            rule_name=f"{prefix}-document-upload-event-rule-{suffix}",
            event_pattern=aws_events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
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

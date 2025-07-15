from aws_cdk import Stack, aws_events, aws_events_targets, aws_sqs
from constructs import Construct


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

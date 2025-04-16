from aws_cdk import (
    Stack,
    aws_lambda,
    aws_sqs,
    aws_lambda_event_sources,
    Duration,
    Tags,
)
from constructs import Construct

class CdkWorkerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values
        tags = self.node.try_get_context('tags')
        naming = self.node.try_get_context('naming')
        prefix = naming['prefix']
        suffix = naming['suffix']

        # Apply tags to all resources in the stack
        for key, value in tags.items():
            Tags.of(self).add(key, value)

        # Define process names
        processes = [
            "document_extract",
            "block_processing",
            "document_summary",
            "seed_questions",
            "feature_extraction"
        ]

        # Create SQS queues and Lambda functions for each process
        for process in processes:
            # Create SQS queue
            queue = aws_sqs.Queue(
                self, f"{process.replace('_', ' ').title().replace(' ', '')}Queue",
                queue_name=f"{prefix}-{process}-queue-{suffix}",
                visibility_timeout=Duration.seconds(300),
                retention_period=Duration.days(14)
            )

            # Create Lambda function
            lambda_fn = aws_lambda.Function(
                self, f"{process.replace('_', ' ').title().replace(' ', '')}Lambda",
                function_name=f"{prefix}-{process}-lambda-{suffix}",
                runtime=aws_lambda.Runtime.PYTHON_3_12,
                handler="index.handler",
                code=aws_lambda.Code.from_asset(f"src/cdk_worker/lambda/{process}"),
                timeout=Duration.seconds(300)
            )

            # Add SQS event source to Lambda
            lambda_fn.add_event_source(
                aws_lambda_event_sources.SqsEventSource(queue)
            )

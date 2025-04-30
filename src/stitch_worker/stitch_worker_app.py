import aws_cdk as cdk
from stitch_worker.stitch_worker_stack import StitchWorkerStack, StitchOrchestrationStack
from stitch_worker import StitchWorkerSettings

app = cdk.App(
    context=dict(settings=StitchWorkerSettings().model_dump()),
)
StitchWorkerStack(
    app,
    "StitchWorkerStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account") or None,  # Use current account
        region=app.node.try_get_context("region") or "us-east-2",  # Default to us-east-2
    ),
)

StitchOrchestrationStack(
    app,
    "StitchOrchestrationStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account") or None,  # Use current account
        region=app.node.try_get_context("region") or "us-east-2",  # Default to us-east-2
    ),
)

app.synth()

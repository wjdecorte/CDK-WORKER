#!/usr/bin/env python3
import aws_cdk as cdk
from stitch_worker.stitch_worker_stack import StitchWorkerStack

app = cdk.App()
StitchWorkerStack(app, "StitchWorkerStack",
    env=cdk.Environment(
        account=app.node.try_get_context('account') or None,  # Use current account
        region=app.node.try_get_context('region') or 'us-east-2'  # Default to us-east-1
    )
)

app.synth()

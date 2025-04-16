#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_worker.cdk_worker_stack import CdkWorkerStack

app = cdk.App()
CdkWorkerStack(app, "CdkWorkerStack",
    env=cdk.Environment(
        account=app.node.try_get_context('account') or None,  # Use current account
        region=app.node.try_get_context('region') or 'us-east-2'  # Default to us-east-1
    )
)

app.synth()

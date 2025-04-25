import json
import time
import boto3
from uuid import uuid4
from random import randint
from typing import Sequence

from pydantic import BaseModel
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import SqsModel, SqsRecordModel

logger = Logger()


class StitchWorkerEventBridgeModel(BaseModel):
    metadata: dict
    data: dict


class SqsStitchWorkerRecordModel(SqsRecordModel):
    body: StitchWorkerEventBridgeModel


class SqsCustomEventNotificationModel(SqsModel):
    Records: Sequence[SqsStitchWorkerRecordModel]


@logger.inject_lambda_context(log_event=True)
@event_parser(model=SqsCustomEventNotificationModel)
def handler(event: SqsCustomEventNotificationModel, context: LambdaContext):
    logger.info(f"Received context: {context=}")

    for record in event.Records:
        custom_event = record.body
        logger.info(f"Generating summary for: {custom_event=}")

        # Add document summarization logic here
        time.sleep(randint(30, 60))
        document_summary_id = str(uuid4())

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker",
                    "DetailType": "DocumentSummaryGenerated",
                    "Detail": json.dumps(
                        {
                            "metadata": {
                                "document_id": custom_event["metadata"]["document_id"],
                                "document_summary_id": document_summary_id,
                            },
                            "data": {"status": "COMPLETED"},
                        }
                    ),
                    "EventBusName": "stitch-dev-datastores-bus",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Document summarization completed successfully")}

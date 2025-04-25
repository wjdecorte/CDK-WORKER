import json
import time
import boto3
from uuid import uuid4
from random import randint
from typing import Sequence, Literal

from pydantic import BaseModel, Json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import SqsModel, SqsRecordModel, EventBridgeModel

logger = Logger()


class StitchWorkerEventBridgeDetailModel(BaseModel):
    metadata: dict
    data: dict


class StitchWorkerEventBridgeModel(EventBridgeModel):
    source: Literal["stitch.worker"]
    detail: StitchWorkerEventBridgeDetailModel


class SqsStitchWorkerRecordModel(SqsRecordModel):
    body: Json[StitchWorkerEventBridgeModel]


class SqsCustomEventNotificationModel(SqsModel):
    Records: Sequence[SqsStitchWorkerRecordModel]


@logger.inject_lambda_context(log_event=True)
@event_parser(model=SqsCustomEventNotificationModel)
def handler(event: SqsCustomEventNotificationModel, context: LambdaContext):
    logger.info(f"Received context: {context=}")

    for record in event.Records:
        custom_event = record.body
        logger.info(f"Generating seed questions for: {custom_event}")

        # Add seed question generation logic here
        time.sleep(randint(30, 60))
        seed_questions_id = str(uuid4())
        seed_questions_list = custom_event.detail.metadata["seed_questions_list"]
        logger.info(f"{seed_questions_list=}")

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker",
                    "DetailType": "SeedQuestionsGenerated",
                    "Detail": json.dumps(
                        {
                            "metadata": {
                                "document_id": custom_event.detail.metadata["document_id"],
                                "seed_questions_id": seed_questions_id,
                            },
                            "data": {"status": "COMPLETED"},
                        }
                    ),
                    "EventBusName": "stitch-dev-datastores-bus",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Seed question generation completed successfully")}

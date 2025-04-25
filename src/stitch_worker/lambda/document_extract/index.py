import json
import time
import boto3
from uuid import uuid4
from random import randint
from typing import Sequence

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import SqsModel, S3EventNotificationEventBridgeModel, SqsRecordModel

logger = Logger()


class S3SqsRecordModel(SqsRecordModel):
    body: S3EventNotificationEventBridgeModel


class SqsS3EventNotificationModel(SqsModel):
    Records: Sequence[SqsRecordModel]


@logger.inject_lambda_context(log_event=True)
@event_parser(model=SqsS3EventNotificationModel)
def handler(event: SqsS3EventNotificationModel, context: LambdaContext):
    logger.info(f"Received context: {context=}")

    for record in event.Records:
        # s3_event = parser.parse(record.body, model=S3EventNotificationEventBridgeModel)
        s3_event = record.body
        logger.info(f"Processing document extraction for: {s3_event=}")

        # Add document extraction logic here
        time.sleep(randint(30, 60))
        document_id = str(uuid4())
        # call Textract Async API
        # textract = boto3.client("textract")
        # response = textract.start_document_text_detection(
        #     DocumentLocation={
        #         "S3Object": {
        #             "Bucket": message["bucket"],
        #             "Name": message["key"]
        #         }
        #     },
        #     OutputConfig={
        #         "S3Bucket": "stitch-textract-output-dev",
        #         "S3KeyPrefix": "textract-output"
        #     }
        # )
        # logger.info(f"Textract Async API response: {response=}")

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker",
                    "DetailType": "DocumentExtractionCompleted",
                    "Detail": json.dumps(
                        {
                            "metadata": {
                                "document_id": document_id,
                                "seed_questions_list": [23, 45, 67],
                                "feature_types": [1, 2, 3],
                            },
                            "data": {"status": "COMPLETED"},
                        }
                    ),
                    "EventBusName": "stitch-dev-datastores-bus",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Document extraction completed successfully")}

import json
import logging
import time
import boto3

from stitch_worker.enums import EventType

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    for record in event["Records"]:
        message = json.loads(record["body"])
        logger.info(f"Processing document extraction for: {message}")

        # Add document extraction logic here
        time.sleep(30)
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
                    "Source": "stitch.worker.document_extract",
                    "DetailType": EventType.DOCUMENT_EXTRACTION_COMPLETED,
                    "Detail": json.dumps({"message": message, "status": "COMPLETED"}),
                    "EventBusName": "stitch-event-bus-dev",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Document extraction completed successfully")}

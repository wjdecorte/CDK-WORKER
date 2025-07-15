import boto3
import json
import os


def handler(event, context):
    try:
        print(f"Received event: {json.dumps(event)}")

        # Check if this is an EC2 instance state change
        if event.get("source") == "aws.ec2" and event.get("detail-type") == "EC2 Instance State-change Notification":
            detail = event.get("detail", {})
            state = detail.get("state")
            instance_id = detail.get("instance-id")

            print(f"EC2 instance {instance_id} state changed to: {state}")

            # Only proceed if instance is running
            if state == "running":
                # Get the instance's public IP
                ec2_client = boto3.client("ec2")
                response = ec2_client.describe_instances(InstanceIds=[instance_id])

                if not response["Reservations"]:
                    print(f"No reservations found for instance {instance_id}")
                    return {"statusCode": 400, "body": "Instance not found"}

                instance = response["Reservations"][0]["Instances"][0]
                public_ip = instance.get("PublicIpAddress", "localhost")
                hub_url = f"http://{public_ip}:5050/hub/api/v1"

                print(f"Instance {instance_id} public IP: {public_ip}")
                print(f"New hub URL: {hub_url}")

                # Update Lambda functions' environment variables
                lambda_client = boto3.client("lambda")

                # Get prefix and suffix from environment or use defaults
                prefix = os.environ.get("PREFIX", "stitch")
                suffix = os.environ.get("SUFFIX", "dev")

                # List all Lambda functions with our prefix
                paginator = lambda_client.get_paginator("list_functions")
                updated_functions = []

                for page in paginator.paginate():
                    for function in page["Functions"]:
                        if function["FunctionName"].startswith(f"{prefix}-{suffix}-"):
                            try:
                                # Get current configuration
                                config_response = lambda_client.get_function_configuration(
                                    FunctionName=function["FunctionName"]
                                )
                                environment = config_response.get("Environment", {})
                                variables = environment.get("Variables", {})

                                # Update HUB_URL if it exists
                                if "HUB_URL" in variables:
                                    old_url = variables["HUB_URL"]
                                    variables["HUB_URL"] = hub_url

                                    # Update the function
                                    lambda_client.update_function_configuration(
                                        FunctionName=function["FunctionName"], Environment={"Variables": variables}
                                    )
                                    updated_functions.append(f"{function['FunctionName']}/HUB_URL")
                                    print(f"Updated {function['FunctionName']} HUB_URL: {old_url} -> {hub_url}")
                                else:
                                    print(f"Skipped {function['FunctionName']} - no HUB_URL found")

                                # Update DATABASE_HOST if it exists
                                if "DATABASE_HOST" in variables:
                                    old_host = variables["DATABASE_HOST"]
                                    variables["DATABASE_HOST"] = public_ip
                                    lambda_client.update_function_configuration(
                                        FunctionName=function["FunctionName"], Environment={"Variables": variables}
                                    )
                                    updated_functions.append(f"{function['FunctionName']}/DATABASE_HOST")
                                    print(
                                        f"Updated {function['FunctionName']} DATABASE_HOST: {old_host} -> {public_ip}"
                                    )
                                else:
                                    print(f"Skipped {function['FunctionName']} - no DATABASE_HOST found")

                            except Exception as e:
                                print(f"Error updating {function['FunctionName']}: {str(e)}")

                print(f"Successfully updated {len(updated_functions)} Lambda functions with new hub URL: {hub_url}")
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "message": "Success",
                            "updated_functions": updated_functions,
                            "hub_url": hub_url,
                            "public_ip": public_ip,
                        }
                    ),
                }
            else:
                print(f"Instance {instance_id} is not running (state: {state}), skipping update")

        return {"statusCode": 200, "body": json.dumps("Event processed (no action needed)")}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}

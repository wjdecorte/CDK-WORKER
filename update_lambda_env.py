#!/usr/bin/env python3
"""
Script to manually update Lambda environment variables with the current EC2 instance IP.
Run this script after your EC2 instance has started to update all Lambda functions.
"""

import boto3
import argparse
import sys


def get_ec2_public_ip(instance_id):
    """Get the public IP address of an EC2 instance"""
    ec2_client = boto3.client("ec2")
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        if not response["Reservations"]:
            raise ValueError(f"No reservations found for instance {instance_id}")

        instance = response["Reservations"][0]["Instances"][0]
        public_ip = instance.get("PublicIpAddress")

        if not public_ip:
            raise ValueError(f"No public IP found for instance {instance_id}")

        return public_ip
    except Exception as e:
        print(f"Error getting EC2 instance IP: {e}")
        sys.exit(1)


def update_lambda_environment_variables(prefix, suffix, hub_url):
    """Update all Lambda functions with the new hub URL"""
    lambda_client = boto3.client("lambda")
    updated_functions = []
    skipped_functions = []
    error_functions = []

    try:
        # List all Lambda functions with our prefix
        paginator = lambda_client.get_paginator("list_functions")

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
                            updated_functions.append(function["FunctionName"])
                            print(f"✅ Updated {function['FunctionName']} HUB_URL: {old_url} -> {hub_url}")
                        else:
                            skipped_functions.append(function["FunctionName"])
                            print(f"⏭️  Skipped {function['FunctionName']} - no HUB_URL found")

                    except Exception as e:
                        error_functions.append(function["FunctionName"])
                        print(f"❌ Error updating {function['FunctionName']}: {str(e)}")

        # Summary
        print("\n📊 Summary:")
        print(f"✅ Updated: {len(updated_functions)} functions")
        print(f"⏭️  Skipped: {len(skipped_functions)} functions")
        print(f"❌ Errors: {len(error_functions)} functions")

        if updated_functions:
            print(f"\n🎯 New hub URL: {hub_url}")
            print(f"📝 Updated functions: {', '.join(updated_functions)}")

        return len(updated_functions) > 0

    except Exception as e:
        print(f"Error listing/updating Lambda functions: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Update Lambda environment variables with EC2 instance IP")
    parser.add_argument("--instance-id", required=True, help="EC2 instance ID")
    parser.add_argument("--prefix", default="stitch", help="Lambda function name prefix")
    parser.add_argument("--suffix", default="dev", help="Lambda function name suffix")
    parser.add_argument("--port", default="5050", help="Hub port number")
    parser.add_argument("--path", default="/hub/api/v1", help="Hub API path")

    args = parser.parse_args()

    print(f"🔍 Getting public IP for instance {args.instance_id}...")
    public_ip = get_ec2_public_ip(args.instance_id)
    hub_url = f"http://{public_ip}:{args.port}{args.path}"

    print(f"🌐 EC2 instance public IP: {public_ip}")
    print(f"🔗 Hub URL: {hub_url}")
    print(f"🔧 Updating Lambda functions with prefix '{args.prefix}-{args.suffix}-'...")

    success = update_lambda_environment_variables(args.prefix, args.suffix, hub_url)

    if success:
        print("\n🎉 Successfully updated Lambda environment variables!")
        print("💡 You can now test your Lambda functions with the new hub URL.")
    else:
        print("\n⚠️  No Lambda functions were updated.")
        sys.exit(1)


if __name__ == "__main__":
    main()

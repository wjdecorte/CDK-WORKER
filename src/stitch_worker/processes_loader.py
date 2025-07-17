import os
import copy
from typing import Any

import yaml
from aws_cdk import aws_iam


def load_processes_config(
    settings: dict[str, Any],
    s3_bucket_name: str,
    document_extraction_topic_arn: str = None,
    document_extraction_role_arn: str = None,
    openai_api_key: str = None,
    pinecone_api_key: str = None,
    pinecone_index_name: str = None,
    ec2_host: str = None,
    database_password: str = None,
) -> list[dict[str, Any]]:
    """
    Load processes configuration from YAML file and substitute template variables.

    Args:
        settings: Settings dictionary containing lambda enable flags
        s3_bucket_name: S3 bucket name
        document_extraction_topic_arn: SNS topic ARN for document extraction
        document_extraction_role_arn: IAM role ARN for document extraction
        openai_api_key: OpenAI API key
        pinecone_api_key: Pinecone API key
        pinecone_index_name: Pinecone index name
        ec2_host: EC2 host
        database_password: Database password

    Returns:
        List of process configurations with substituted values
    """
    # Get the directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(current_dir, "processes.yaml")

    with open(yaml_path, "r") as file:
        config = yaml.safe_load(file)

    processes = config["processes"]

    # Template variable mapping
    template_vars: dict[str, Any] = {}

    # Add all settings values dynamically with ${key} format
    for key, value in settings.items():
        template_vars[f"${{{key}}}"] = value

    # Add explicit mappings for backward compatibility and special cases
    explicit_mappings = {
        "${s3_bucket_name}": s3_bucket_name,
        "${document_extraction_topic_arn}": document_extraction_topic_arn or "",
        "${document_extraction_role_arn}": document_extraction_role_arn or "",
        "${openai_api_key}": openai_api_key or "",
        "${pinecone_api_key}": pinecone_api_key or "",
        "${pinecone_index_name}": pinecone_index_name or "",
        "${database_host}": settings.get("database_host") or ec2_host,
        "${database_port}": settings.get("database_port"),
        "${database_name}": settings.get("database_name"),
        "${database_user}": settings.get("database_user"),
        "${database_password}": database_password or "",
    }

    # Update template_vars with explicit mappings (these will override dynamic ones if there are conflicts)
    template_vars.update(explicit_mappings)

    processed_processes = []

    for process in processes:
        # Deep copy the process to avoid modifying the original
        processed_process = copy.deepcopy(process)

        # Substitute template variables in the process
        processed_process = _substitute_template_vars(processed_process, template_vars)

        # Convert policy definitions to IAM PolicyStatement objects
        if "additional_policies" in processed_process:
            policies = []
            for policy_def in processed_process["additional_policies"]:
                if policy_def:  # Skip empty policies
                    policy = aws_iam.PolicyStatement(
                        effect=getattr(aws_iam.Effect, policy_def["effect"]),
                        actions=policy_def["actions"],
                        resources=policy_def["resources"],
                    )
                    policies.append(policy)
            processed_process["additional_policies"] = policies

        processed_processes.append(processed_process)

    return processed_processes


def _substitute_template_vars(obj: Any, template_vars: dict[str, Any]) -> Any:
    """
    Recursively substitute template variables in a nested structure.

    Args:
        obj: Object to process (can be dict, list, or primitive)
        template_vars: Dictionary of template variables and their values

    Returns:
        Object with template variables substituted
    """
    if isinstance(obj, dict):
        return {key: _substitute_template_vars(value, template_vars) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_template_vars(item, template_vars) for item in obj]
    elif isinstance(obj, str):
        # Check if the string is exactly a template variable
        if obj in template_vars:
            return template_vars[obj]

        # Substitute template variables in strings
        result = obj
        for var, value in template_vars.items():
            result = result.replace(var, str(value))
        return result
    else:
        return obj

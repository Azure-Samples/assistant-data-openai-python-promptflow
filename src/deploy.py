"""Deploy a flow to Azure AI."""

# enable type annotation syntax on Python versions earlier than 3.9
from __future__ import annotations

# set environment variables before importing any other code (in particular the openai module)
from dotenv import load_dotenv

load_dotenv()

import os
import sys
import asyncio
import platform
from typing import List

import argparse
import logging
import os

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
    BuildContext,
)


def get_arg_parser(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    """Get the argument parser for the script."""
    if parser is None:
        parser = argparse.ArgumentParser(__doc__)

    parser.add_argument(
        "--flow-path",
        help="Path to the flow",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--deployment-name",
        help="deployment name to use when deploying or invoking the flow",
        type=str,
        default="assistants-orchestrator-deployment",
    )
    parser.add_argument(
        "--endpoint-name",
        help="endpoint name to use when deploying or invoking the flow",
        type=str,
        default="assistants-orchestrator-endpoint",
    )
    parser.add_argument(
        "--instance-type",
        help="instance type to use for the deployment",
        type=str,
        default="Standard_E16s_v3",
    )
    parser.add_argument(
        "--instance-count",
        help="instance count to use for the deployment",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--verbose",
        help="enable verbose logging",
        action="store_true",
    )

    return parser


def main(cli_args: List[str] = None):
    """Main entry point for the script."""
    parser = get_arg_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # turn off some dependencies logs
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)

    logging.info(f"Connecting to Azure AI project...")
    if "AZURE_SUBSCRIPTION_ID" not in os.environ:
        # if not using environment variables, you can use the config.json file
        client = MLClient.from_config()
    else:
        # if using environment variables
        client = MLClient(
            credential=DefaultAzureCredential(),
            subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID"),
            resource_group_name=os.environ.get("AZURE_RESOURCE_GROUP"),
            project_name=os.environ.get("AZURE_AI_PROJECT_NAME"),
            ai_resource_name=os.environ.get("AZURE_AI_RESOURCE_NAME"),
        )

    # specify the endpoint creation settings
    endpoint = ManagedOnlineEndpoint(
        name=args.endpoint_name,
        properties={
            "enforce_access_to_default_secret_stores": "enabled"  # if you want secret injection support
        },
    )
    logging.info(f"Will create endpoint: {endpoint}")

    model = Model(
        path=args.flow_path,
    )

    logging.info(f"Packaged flow as a model for deployment: {model}")

    # create an environment for the deployment
    environment = Environment(  # when pf is a model type, the environment section will not be required at all
        build=BuildContext(
            path=args.flow_path,
        ),
        inference_config={
            "liveness_route": {
                "path": "/health",
                "port": 8080,
            },
            "readiness_route": {
                "path": "/health",
                "port": 8080,
            },
            "scoring_route": {
                "path": "/score",
                "port": 8080,
            },
        },
    )

    # at deployment time, environment variables will be resolved from the connections
    environment_variables = {
        # those first variables are drawing from the hub connections
        "AZURE_OPENAI_ENDPOINT": "${{azureml://connections/Default_AzureOpenAI/target}}",
        "AZURE_OPENAI_KEY": "${{azureml://connections/Default_AzureOpenAI/credentials/key}}",
        "AZURE_OPENAI_API_VERSION": "${{azureml://connections/Default_AzureOpenAI/metadata/ApiVersion}}",
        "AZURE_AI_SEARCH_ENDPOINT": "${{azureml://connections/AzureAISearch/target}}",
        "AZURE_AI_SEARCH_KEY": "${{azureml://connections/AzureAISearch/credentials/key}}",
        # the remaining ones can be set based on local environment variables
        "AZURE_AI_SEARCH_INDEX_NAME": os.getenv("AZURE_AI_SEARCH_INDEX_NAME"),
        "AZURE_OPENAI_CHAT_MODEL": os.getenv("AZURE_OPENAI_CHAT_MODEL"),
        "AZURE_OPENAI_CHAT_DEPLOYMENT": os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        "AZURE_OPENAI_EVALUATION_MODEL": os.getenv("AZURE_OPENAI_EVALUATION_MODEL"),
        "AZURE_OPENAI_EVALUATION_DEPLOYMENT": os.getenv(
            "AZURE_OPENAI_EVALUATION_DEPLOYMENT"
        ),
        "AZURE_OPENAI_EMBEDDING_MODEL": os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        ),
    }

    # NOTE: fix
    environment_variables["PRT_CONFIG_OVERRIDE"] = (
        f"deployment.subscription_id={client.subscription_id},deployment.resource_group={client.resource_group_name},deployment.workspace_name={client.workspace_name},deployment.endpoint_name={endpoint_name},deployment.deployment_name={deployment_name}"
    )

    # specify the deployment creation settings
    deployment = ManagedOnlineDeployment(  # defaults to key auth_mode
        name=args.deployment_name,
        endpoint_name=args.endpoint_name,
        model=model,  # path to promptflow folder
        environment=environment,
        instance_type=args.instance_type,  # can point to documentation for this: https://learn.microsoft.com/en-us/azure/machine-learning/reference-managed-online-endpoints-vm-sku-list?view=azureml-api-2
        instance_count=args.instance_count,
        environment_variables=environment_variables,
    )

    # 1. create endpoint
    created_endpoint = client.begin_create_or_update(
        endpoint
    ).result()  # result() means we wait on this to complete - currently endpoint doesnt have any status, but then deployment does have status

    # 2. create deployment
    created_deployment = client.begin_create_or_update(deployment).result()

    # 3. update endpoint traffic for the deployment
    endpoint.traffic = {args.deployment_name: 100}  # set to 100% of traffic
    client.begin_create_or_update(endpoint).result()


if __name__ == "__main__":
    main()

"""Deploy a flow to Azure AI."""

import os
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

from dotenv import load_dotenv

load_dotenv()


def get_arg_parser(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    """Get the argument parser for the script."""
    if parser is None:
        parser = argparse.ArgumentParser(__doc__)

    parser.add_argument(
        "--flow-path",
        help="Path to the flow",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "copilot_sdk_flow"),
    )
    parser.add_argument(
        "--aoai-connection-name",
        help="Azure OpenAI connection name to use for the deployment",
        type=str,
        default="aoai-connection",
    )
    parser.add_argument(
        "--deployment-name",
        help="deployment name to use when deploying or invoking the flow",
        type=str,
        default="assistants-flow-deployment",
    )
    parser.add_argument(
        "--endpoint-name",
        help="endpoint name to use when deploying or invoking the flow",
        type=str,
        default=os.getenv("AZUREAI_ENDPOINT_NAME"),
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


def get_ml_client() -> MLClient:
    """Get the ML client for the script."""
    if "AZURE_SUBSCRIPTION_ID" not in os.environ:
        # if not using environment variables, you can use the config.json file
        logging.info("Using config.json file for authentication")
        ml_client = MLClient.from_config()
    else:
        # if using environment variables
        logging.info(
            f"Connecting to Azure AI project {os.environ.get('AZUREAI_PROJECT_NAME')}..."
        )
        ml_client = MLClient(
            credential=DefaultAzureCredential(),
            subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID"),
            resource_group_name=os.environ.get("AZURE_RESOURCE_GROUP"),
            workspace_name=os.environ.get("AZUREAI_PROJECT_NAME"),
        )

    # test the client before going further
    ml_client.workspaces.get(os.environ.get("AZUREAI_PROJECT_NAME"))
    return ml_client


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

    client = get_ml_client()

    # specify the endpoint creation settings
    try:
        endpoint = client.online_endpoints.get(args.endpoint_name)
        logging.info(f"Found existing endpoint: {args.endpoint_name}")
    except:
        logging.info(f"Endpoint {args.endpoint_name} not found, creating a new one...")
        endpoint = ManagedOnlineEndpoint(
            name=args.endpoint_name,
            properties={
                "enforce_access_to_default_secret_stores": "enabled"  # if you want secret injection support
            },
        )

    model = Model(
        name="copilot_flow_model",
        path=args.flow_path,  # path to promptflow folder
        properties=[  # this enables the chat interface in the endpoint test tab
            ["azureml.promptflow.source_flow_id", "basic-chat"],
            ["azureml.promptflow.mode", "chat"],
            ["azureml.promptflow.chat_input", "chat_input"],
            ["azureml.promptflow.chat_output", "reply"],
        ],
    )
    logging.info("Packaged flow as a model for deployment")

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

    connection_string = f"azureml://connections/{args.aoai_connection_name}"
    logging.info(f"Using connection: {connection_string}")

    # at deployment time, environment variables will be resolved from the connections
    environment_variables = {
        # those first variables are drawing from the hub connections
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT")
        or "${{" + connection_string + "/target}}",
        "AZURE_OPENAI_ASSISTANT_ID": os.getenv("AZURE_OPENAI_ASSISTANT_ID"),
        "AZURE_OPENAI_API_VERSION": os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
        ),
        "AZURE_OPENAI_CHAT_DEPLOYMENT": os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
    }
    if "AZURE_OPENAI_API_KEY" in os.environ:
        logging.warn(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        logging.info(
            f"The key will not be injected from your environment, but from the Project connection '{args.aoai_connection_name}'."
        )
        environment_variables["AZURE_OPENAI_API_KEY"] = os.getenv(
            "${{" + connection_string + "/credentials/key}}"
        )

    # NOTE: this is a required fix
    environment_variables["PRT_CONFIG_OVERRIDE"] = (
        f"deployment.subscription_id={client.subscription_id},deployment.resource_group={client.resource_group_name},deployment.workspace_name={client.workspace_name},deployment.endpoint_name={args.endpoint_name},deployment.deployment_name={args.deployment_name}"
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
    print(f"Creating/updating endpoint {args.endpoint_name}...")
    created_endpoint = client.begin_create_or_update(
        endpoint
    ).result()  # result() means we wait on this to complete - currently endpoint doesnt have any status, but then deployment does have status

    # 2. create deployment
    print(f"Creating/updating deployment {args.deployment_name}...")
    created_deployment = client.begin_create_or_update(deployment).result()

    # 3. update endpoint traffic for the deployment
    endpoint.traffic = {args.deployment_name: 100}  # set to 100% of traffic
    client.begin_create_or_update(endpoint).result()

    print(f"Your online endpoint name is: {created_endpoint}")
    print(f"Your deployment name is: {created_deployment}")
    return created_endpoint, created_deployment


if __name__ == "__main__":
    main()

"""Provision Azure AI resources for you."""

import logging
import os
import sys
import argparse
from pydantic import BaseModel
from omegaconf import OmegaConf

# from azure.ai.ml.entities import Project, Hub
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient


def get_arg_parser(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(__doc__)

    parser.add_argument(
        "--config",
        help="yaml config",
        required=True,
        type=str,
    )

    return parser


##################################
# Resource configuration classes #
##################################


class AzureAIHubConfig(BaseModel):
    subscription_id: str
    resource_group_name: str
    hub_name: str


class AzureAIProjectConfig(BaseModel):
    subscription_id: str
    resource_group_name: str
    hub_name: str
    project_name: str


class AzureAISearchConfig(BaseModel):
    subscription_id: str
    resource_group_name: str
    search_resource_name: str


class AzureOpenAIConfig(BaseModel):
    subscription_id: str
    resource_group_name: str
    aoai_resource_name: str


class AzureOpenAIDeploymentConfig(BaseModel):
    name: str
    model: str


def parse_config(config):
    """Parse the config file."""
    # Basic config check
    if config.ai is None:
        raise ValueError("No AI resources in config.")

    ai_hub = AzureAIHubConfig(
        subscription_id=config.ai.subscription_id,
        resource_group_name=config.ai.resource_group_name,
        hub_name=config.ai.hub_name,
    )
    ai_project = AzureAIProjectConfig(
        subscription_id=config.ai.subscription_id,
        resource_group_name=config.ai.resource_group_name,
        hub_name=config.ai.hub_name,
        project_name=config.ai.project_name,
    )

    if config.search is None:
        raise ValueError("No AI Search resources in config.")

    ai_search = AzureAISearchConfig(
        subscription_id=config.search.subscription_id,
        resource_group_name=config.search.resource_group_name,
        search_resource_name=config.search.search_resource_name,
    )

    if config.aoai is None:
        raise ValueError("No Azure OpenAI resources in config.")

    aoai = AzureOpenAIConfig(
        subscription_id=config.aoai.subscription_id,
        resource_group_name=config.aoai.resource_group_name,
        aoai_resource_name=config.aoai.aoai_resource_name,
    )

    return ai_hub, ai_project, ai_search, aoai


#################################
# Resource management functions #
#################################


def check_ai_hub_exists(ai_hub: AzureAIHubConfig) -> bool:
    """Check if the AI Hub resource exists."""
    ml_client = MLClient(
        subscription_id=ai_hub.subscription_id,
        resource_group_name=ai_hub.resource_group_name,
        credential=DefaultAzureCredential(),
    )

    try:
        created_hub = ml_client.workspaces.get(ai_hub.hub_name)
        return True
    except Exception as e:
        return False


def check_ai_project_exists(ai_project: AzureAIProjectConfig) -> bool:
    """Check if the AI Hub resource exists."""
    ml_client = MLClient(
        subscription_id=ai_project.subscription_id,
        resource_group_name=ai_project.resource_group_name,
        credential=DefaultAzureCredential(),
    )

    try:
        created_hub = ml_client.workspaces.get(ai_project.hub_name)
        created_project = ml_client.workspaces.get(ai_project.project_name)
        return True
    except Exception as e:
        return False


def check_ai_search_exists(ai_search: AzureAISearchConfig) -> bool:
    client = SearchManagementClient(
        credential=DefaultAzureCredential(), subscription_id=ai_search.subscription_id
    )

    try:
        response = client.services.get(
            resource_group_name=ai_search.resource_group_name,
            search_service_name=ai_search.search_resource_name,
        )
        return True
    except Exception as e:
        return False


def check_aoai_exists(aoai: AzureOpenAIConfig) -> bool:
    client = CognitiveServicesManagementClient(
        credential=DefaultAzureCredential(), subscription_id=aoai.subscription_id
    )

    try:
        response = client.accounts.get(
            resource_group_name=aoai.resource_group_name,
            account_name=aoai.aoai_resource_name,
        )
        return True
    except Exception as e:
        return False


def build_provision_plan(config):
    """Depending on values in config, creates a provisioning plan."""
    ai_hub, ai_project, ai_search, aoai = parse_config(config)
    plan = []

    # AI hub and project checks
    if check_ai_hub_exists(ai_hub):
        logging.info(f"AI Hub {ai_hub.hub_name} already exists.")
        if check_ai_project_exists(ai_project):
            logging.info(f"AI Project {ai_project.project_name} already exists.")
        else:
            logging.info(
                f"AI Project {ai_project.project_name} does not exist. Adding to provisioning plan..."
            )
            plan.append(f"create_project({ai_project})")
    else:
        logging.info(
            f"AI Hub {ai_hub.hub_name} does not exist. Adding to provisioning plan..."
        )
        plan.append(f"create_hub({ai_hub})")
        plan.append(f"create_project({ai_project})")

    # Search resource
    if check_ai_search_exists(ai_search):
        logging.info(f"AI Search {ai_search.search_resource_name} already exists.")
    else:
        logging.info(
            f"AI Search {ai_search.search_resource_name} does not exist. Adding to provisioning plan..."
        )
        plan.append(f"create_search({ai_search})")

    # AOAI resource
    if check_aoai_exists(aoai):
        logging.info(f"Azure OpenAI {aoai.aoai_resource_name} already exists.")
    else:
        logging.info(
            f"Azure OpenAI {aoai.aoai_resource_name} does not exist. Adding to provisioning plan..."
        )
        plan.append(f"create_aoai({aoai})")

    return plan


def main():
    """Provision Azure AI resources for you."""
    parser = get_arg_parser()
    args, _ = parser.parse_known_args()

    config = OmegaConf.load(args.config)
    provision_plan = build_provision_plan(config)

    print("Here's the resulting provisioning plan:")
    for step in provision_plan:
        print(step)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # exclude azure.* from logging
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    main()

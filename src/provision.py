"""Provision Azure AI resources for you."""

"""
TODO: get url from dan's code
- script can fail in certain types
    - sub id has a typo
    - dotenv is appending, not overwriting
- parameter --config is confusing, use --spec instead?
- use a combination of config.json
- upgrade to azure-ai-ml

"""
import logging
import os
import sys
import re
import argparse
from pydantic import BaseModel
from omegaconf import OmegaConf
from collections import OrderedDict

# from azure.ai.ml.entities import Project, Hub
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.resource import ResourceManagementClient

# from azure.ai.ml.entities import Project,Hub
from azure.ai.ml.entities import (
    Hub,  # TODO: need to replace with Hub
    Project,  # TODO: need to replace with Project
    AzureOpenAIConnection,
    AzureAISearchConnection,
    ApiKeyConfiguration,
)

from typing import List, Callable, Dict, Any, Optional, Union


def get_arg_parser(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(__doc__)

    parser.add_argument(
        "--verbose",
        help="Enable verbose logging",
        action="store_true",
    )
    parser.add_argument(
        "--config",
        help="yaml config",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--provision",
        help="Provision resources",
        action="store_true",
    )
    parser.add_argument(
        "--export-env",
        help="Export environment variables into a file",
        default=None,
    )

    return parser


#################################
# Resource provisioning classes #
#################################


class ResourceGroup(BaseModel):
    subscription_id: str
    resource_group_name: str
    region: str

    def exists(self) -> bool:
        """Check if the resource group exists."""
        # use ResourceManagementClient
        client = ResourceManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            response = client.resource_groups.get(self.resource_group_name)
            return True
        except Exception as e:
            return False

    def create(self) -> Any:
        """Create a resource group."""
        client = ResourceManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        response = client.resource_groups.create_or_update(
            resource_group_name=self.resource_group_name,
            parameters={"location": self.region},
        )
        return response


class AzureAIHub(BaseModel):
    subscription_id: str
    resource_group_name: str
    hub_name: str
    region: str

    def exists(self) -> bool:
        """Check if the resource exists."""
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        try:
            created_hub = ml_client.workspaces.get(self.hub_name)
            logging.debug(f"hub found: {created_hub}")
            return True
        except Exception as e:
            logging.debug(f"hub not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Hub {self.hub_name}...")
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        hub = Hub(
            name=self.hub_name,
            location="westus",
            resource_group=self.resource_group_name,
        )
        response = ml_client.workspaces.begin_create(hub).result()
        return response


class AzureAIProject(BaseModel):
    subscription_id: str
    resource_group_name: str
    hub_name: str
    project_name: str
    region: str

    def exists(self) -> bool:
        """Check if the resource exists."""
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        try:
            created_hub = ml_client.workspaces.get(self.hub_name)
            created_project = ml_client.workspaces.get(self.project_name)
            logging.debug(f"project found: {created_project}")
            return True
        except Exception as e:
            logging.debug(f"project not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Project {self.project_name}...")
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        hub = ml_client.workspaces.get(self.hub_name)

        project = Project(
            name=self.project_name,
            hub_id=hub.id,
            location=hub.location,
            resource_group=hub.resource_group,
        )
        response = ml_client.workspaces.begin_create(project).result()

        return response


class AzureAISearch(BaseModel):
    subscription_id: str
    resource_group_name: str
    search_resource_name: str
    region: str

    def exists(self) -> bool:
        """Check if the resource exists."""
        client = SearchManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            resource = client.services.get(
                resource_group_name=self.resource_group_name,
                search_service_name=self.search_resource_name,
            )
            logging.debug(f"search found: {resource}")
            return True
        except Exception as e:
            logging.debug(f"search not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Search {self.search_resource_name}...")
        client = SearchManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        search = client.services.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            search_service_name=self.search_resource_name,
            service={
                "location": self.region,
                # "properties": {"hostingMode": "default", "partitionCount": 1, "replicaCount": 3},
                "sku": {"name": "standard"},
                # "tags": {"app-name": "My e-commerce app"},
            },
        ).result()
        return search


class AzureOpenAIResource(BaseModel):
    subscription_id: str
    resource_group_name: str
    aoai_resource_name: str
    region: str

    def exists(self) -> bool:
        """Check if the resource exists."""
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            account = client.accounts.get(
                resource_group_name=self.resource_group_name,
                account_name=self.aoai_resource_name,
            )
            logging.debug(f"aoai found: {account}")
            return True
        except Exception as e:
            logging.debug(f"aoai not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating Azure OpenAI {self.aoai_resource_name}...")
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        account = client.accounts.begin_create(
            resource_group_name=self.resource_group_name,
            account_name=self.aoai_resource_name,
            account={
                "sku": {"name": "S0"},
                "kind": "OpenAI",
                "location": self.region,
            },
        ).result()
        return account


class AzureOpenAIDeployment(BaseModel):
    resource: AzureOpenAIResource
    name: str
    model: str
    version: Optional[str] = None

    def exists(self) -> bool:
        """Check if the deployment exists."""
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(),
            subscription_id=self.resource.subscription_id,
        )

        try:
            deployment = client.deployments.get(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
                deployment_name=self.name,
            )
            logging.debug(f"aoai deployment found: {deployment}")
            return True
        except Exception as e:
            logging.debug(f"aoai deployment not found: {e}")
            return False

    def create(self) -> Any:
        """Create the deployment"""
        logging.info(f"Creating Azure OpenAI deployment {self.name}...")
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(),
            subscription_id=self.resource.subscription_id,
        )
        deployment = client.deployments.begin_create_or_update(
            resource_group_name=self.resource.resource_group_name,
            deployment_name=self.name,
            account_name=self.resource.aoai_resource_name,
            deployment={
                "properties": {
                    "model": {
                        "format": "OpenAI",
                        "name": self.model,
                        "version": self.version,
                    }
                },
                "sku": {"capacity": 10, "name": "Standard"},
            },
        ).result()
        return deployment


class ConnectionSpec(BaseModel):
    hub: AzureAIHub
    resource: Union[AzureAISearch, AzureOpenAIResource]
    name: str
    auth: str

    def exists(self) -> bool:
        """Check if the connection in AI Hub exists."""
        try:
            ml_client = MLClient(
                subscription_id=self.hub.subscription_id,
                resource_group_name=self.hub.resource_group_name,
                workspace_name=self.hub.hub_name,
                credential=DefaultAzureCredential(),
            )
            created_connection = ml_client.connections.get(self.name)
            logging.debug(f"connection found: {created_connection}")
            return True
        except Exception as e:
            logging.debug(f"connection not found: {e}")
            return False

    def create(self) -> Any:
        """Create the connection in AI Hub."""
        ml_client = MLClient(
            subscription_id=self.hub.subscription_id,
            resource_group_name=self.hub.resource_group_name,
            workspace_name=self.hub.hub_name,
            credential=DefaultAzureCredential(),
        )
        if isinstance(self.resource, AzureAISearch):
            # get search client
            rsc_client = SearchManagementClient(
                credential=DefaultAzureCredential(),
                subscription_id=self.resource.subscription_id,
            )

            # get resource endpoint and keys
            resource = rsc_client.services.get(
                resource_group_name=self.resource.resource_group_name,
                search_service_name=self.resource.search_resource_name,
            )

            # TODO: need better
            resource_target = (
                f"https://{self.resource.search_resource_name}.search.windows.net"
            )

            # get keys
            rsc_keys = rsc_client.admin_keys.get(
                resource_group_name=self.resource.resource_group_name,
                search_service_name=self.resource.search_resource_name,
            )

            # specify connection
            connection_config = AzureAISearchConnection(
                endpoint=resource_target,
                api_key=rsc_keys.primary_key,  # using key-based auth
                name=self.name,
            )

            # create connection
            return ml_client.connections.create_or_update(connection=connection_config)
        if isinstance(self.resource, AzureOpenAIResource):
            rsc_client = CognitiveServicesManagementClient(
                credential=DefaultAzureCredential(),
                subscription_id=self.resource.subscription_id,
            )

            # get endpoint
            resource_target = rsc_client.accounts.get(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
            ).properties.endpoint

            # get keys
            rsc_keys = rsc_client.accounts.list_keys(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
            )

            # specify connection
            connection_config = AzureOpenAIConnection(
                azure_endpoint=resource_target,
                api_key=rsc_keys.key1,  # using key-based auth
                name=self.name,
            )

            # create connection
            return ml_client.connections.create_or_update(connection=connection_config)
        else:
            raise ValueError(f"Unknown connection type: {self.resource.type}")


#####################
# Provisioning Plan #
#####################


class ProvisioningPlan:
    def __init__(self):
        self.steps = OrderedDict()

    def _add_step(self, key, resource):
        if key in self.steps:
            # disregard duplicates
            logging.debug(f"discarding duplicate key {key}")
        else:
            self.steps[key] = resource

    def add_resource(self, resource: Any):
        if isinstance(resource, ResourceGroup):
            key = f"{resource.subscription_id}/{resource.resource_group_name}"
            self._add_step(key, resource)
        elif isinstance(resource, AzureAIHub):
            key = f"{resource.subscription_id}/{resource.resource_group_name}/{resource.hub_name}"
            self._add_step(key, resource)
        elif isinstance(resource, AzureAIProject):
            key = f"{resource.subscription_id}/{resource.resource_group_name}/{resource.hub_name}/{resource.project_name}"
            self._add_step(key, resource)
        elif isinstance(resource, AzureAISearch):
            key = f"{resource.subscription_id}/{resource.resource_group_name}/{resource.search_resource_name}"
            self._add_step(key, resource)
        elif isinstance(resource, AzureOpenAIResource):
            key = f"{resource.subscription_id}/{resource.resource_group_name}/{resource.aoai_resource_name}"
            self._add_step(key, resource)
        elif isinstance(resource, AzureOpenAIDeployment):
            key = f"{resource.resource.subscription_id}/{resource.resource.resource_group_name}/{resource.resource.aoai_resource_name}/{resource.name}"
            self._add_step(key, resource)
        elif isinstance(resource, ConnectionSpec):
            key = f"{resource.hub.subscription_id}/{resource.hub.resource_group_name}/{resource.hub.hub_name}/{resource.name}"
            self._add_step(key, resource)
        else:
            raise ValueError(f"Unknown resource type: {resource}")

    def remove_existing(self):
        """Remove existing resources from the plan."""
        remove_keys = []
        for k in self.steps:
            if self.steps[k].exists():
                logging.info(f"Resource {k} already exists, skipping.")
                remove_keys.append(k)
            else:
                logging.info(f"Resource {k} does not exist, will be added to plan.")

        for k in remove_keys:
            del self.steps[k]

    def provision(self):
        """Provision resources in the plan."""
        for k in self.steps:
            logging.info(f"Provisioning resource {k}...")
            self.steps[k].create()

    def get_main_ai_hub(self):
        for k in self.steps:
            if isinstance(self.steps[k], AzureAIHub):
                return self.steps[k]
        return None

    def get_main_ai_project(self):
        for k in self.steps:
            if isinstance(self.steps[k], AzureAIProject):
                return self.steps[k]
        return None


########
# MAIN #
########


def build_provision_plan(config) -> ProvisioningPlan:
    """Depending on values in config, creates a provisioning plan."""
    plan = ProvisioningPlan()

    # Azure AI Hub
    if config.ai is None:
        raise ValueError("No AI resources in config.")
    plan.add_resource(
        ResourceGroup(
            subscription_id=config.ai.subscription_id,
            resource_group_name=config.ai.resource_group_name,
            region=config.ai.region,
        )
    )
    ai_hub = AzureAIHub(
        subscription_id=config.ai.subscription_id,
        resource_group_name=config.ai.resource_group_name,
        hub_name=config.ai.hub_name,
        region=config.ai.region,
    )
    plan.add_resource(ai_hub)

    assert (
        config.ai.hub_name != config.ai.project_name
    ), "AI hub_name cannot be the same as project_name"

    # Azure AI Project
    plan.add_resource(
        AzureAIProject(
            subscription_id=config.ai.subscription_id,
            resource_group_name=config.ai.resource_group_name,
            hub_name=config.ai.hub_name,
            project_name=config.ai.project_name,
            region=config.ai.region,
        )
    )

    # Search resource
    if hasattr(config, "search") and config.search is not None:
        plan.add_resource(
            ResourceGroup(
                subscription_id=config.search.subscription_id,
                resource_group_name=config.search.resource_group_name,
                region=config.search.region,
            )
        )
        search = AzureAISearch(
            subscription_id=config.search.subscription_id,
            resource_group_name=config.search.resource_group_name,
            search_resource_name=config.search.search_resource_name,
            region=config.search.region,
        )
        plan.add_resource(search)
        plan.add_resource(
            ConnectionSpec(
                hub=ai_hub,
                name=config.search.connection_name,
                auth="key",
                resource=search,
            )
        )

    # AOAI resource
    plan.add_resource(
        ResourceGroup(
            subscription_id=config.aoai.subscription_id,
            resource_group_name=config.aoai.resource_group_name,
            region=config.aoai.region,
        )
    )
    aoai = AzureOpenAIResource(
        subscription_id=config.aoai.subscription_id,
        resource_group_name=config.aoai.resource_group_name,
        aoai_resource_name=config.aoai.aoai_resource_name,
        region=config.aoai.region,
    )
    plan.add_resource(aoai)
    plan.add_resource(
        ConnectionSpec(
            hub=ai_hub, name=config.aoai.connection_name, auth="key", resource=aoai
        )
    )

    if config.aoai.deployments:
        for deployment in config.aoai.deployments:
            plan.add_resource(
                AzureOpenAIDeployment(
                    resource=aoai,
                    name=deployment.name,
                    model=deployment.model,
                    version=(
                        deployment.version if hasattr(deployment, "version") else None
                    ),
                )
            )

    return plan


def build_environment(environment_config, ai_project, env_file_path):
    """Get endpoints and keys from the config into the environment (dotenv)."""
    # connect to AI Hub
    ml_client = MLClient(
        subscription_id=ai_project.subscription_id,
        resource_group_name=ai_project.resource_group_name,
        workspace_name=ai_project.hub_name,
        credential=DefaultAzureCredential(),
    )

    with open(env_file_path, "a") as f:
        logging.info(f"Writing AI Studio references as env vars")
        f.write(f"AZURE_SUBSCRIPTION_ID={ai_project.subscription_id}\n")
        f.write(f"AZURE_RESOURCE_GROUP={ai_project.resource_group_name}\n")
        f.write(f"AZURE_AI_HUB_NAME={ai_project.hub_name}\n")
        f.write(f"AZURE_AI_PROJECT_NAME={ai_project.project_name}\n")

    for key in environment_config.variables.keys():
        conn_str = environment_config.variables[key]

        # write constants directly
        if not conn_str.startswith("azureml://"):
            with open(env_file_path, "a") as f:
                logging.info(f"Writing {key} to {env_file_path}")
                f.write(f"{key}={conn_str}\n")
            continue

        # regex extract connection name and type from
        # "azureml://connections/NAME/SUFFIX"
        try:
            # suffix can be either /target or /credentials/key
            name, suffix = re.match(
                r"azureml://connections/([^/]+)/(.*)", conn_str
            ).groups()
            # name, type = re.match(r"azureml://connections/(.*)/(.*)", conn_str).groups()
        except AttributeError:
            logging.critical(f"Invalid connection string: {conn_str}")
            continue

        logging.info(f"Getting connection {name}...")

        # get connection
        connection = ml_client.connections.get(name)
        print(connection.__dict__)
        if suffix == "target":
            # get target endpoint
            value = connection.target
        elif suffix == "credentials/key":
            # get key itself
            value = connection.credentials.get(key="api_key")
            if value is None:
                logging.error(f"Key {name} not found in connection {conn_str}")
                continue
        else:
            raise NotImplementedError(
                f"Unsupported connection string: {conn_str} (expecting suffix /target or /credentials/key, got {suffix})"
            )

        with open(env_file_path, "a") as f:
            logging.info(f"Writing {key} to {env_file_path}")
            f.write(f"{key}={value}\n")


def main():
    """Provision Azure AI resources for you."""
    parser = get_arg_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # exclude azure.* from logging
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    config = OmegaConf.load(args.config)
    provision_plan = build_provision_plan(config)

    # save ai_project for commodity
    ai_project = provision_plan.get_main_ai_project()

    # remove from the plan resources that already exist
    provision_plan.remove_existing()

    if provision_plan.steps == {}:
        logging.info("All resources already exist, nothing to do.")
    else:
        print("Here's the resulting provisioning plan:")
        for step_key in provision_plan.steps:
            print(str(provision_plan.steps[step_key]))

    if args.provision:
        # provision all resources remaining
        provision_plan.provision()

    if args.export_env:
        logging.info(f"Building environment into {args.export_env}")
        build_environment(config.environment, ai_project, args.export_env)


if __name__ == "__main__":
    main()

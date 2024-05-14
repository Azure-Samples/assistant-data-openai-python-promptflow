import os
import logging
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
import json

# Initialize credentials
credential = DefaultAzureCredential()

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
)

# # Get the quota for a specific model (e.g., GPT-4-Turbo)
# model_name = "GPT-4-Turbo"

# # Retrieve the quota
# quota = service_client.models.get_quota(subscription_id, region, model_name)

# print(f"Quota for {model_name} in {region}: {quota.tpm} TPM")

# list of candidate models we need
CANDIDATE_MODELS = [
    {"name": "gpt-35-turbo", "version": "1106"},
    {"name": "gpt-4", "version": "1106-Preview"},
]

# list of regions in which to look for candidate models
CANDIDATE_LOCATIONS = [
    "australiaeast",
    "eastus",
    "eastus2",
    "francecentral",
    "norwayeast",
    "swedencentral",
    "uksouth",
]


def fetch_quota(client, locations, models):
    """Fetch the quota for the specified models in the specified locations.

    Args:
        client (CognitiveServicesManagementClient): The client to use to fetch the quota.
        locations (list): The list of locations to search for the models.
        models (list): The list of models to search for, see CANDIDATE_MODELS
    """
    fetched_quotas_table = []

    for location in locations:
        print(f"Fetching quotas for the candidate models in {location}")
        for model in client.models.list(location=location):
            for _model in models:
                if model.model.name == _model["name"] and (
                    model.model.version == _model["version"] or _model["version"] == "*"
                ):
                    for sku in model.model.skus:
                        if sku.name == "ProvisionedManaged":
                            fetched_quotas_table.append(
                                {
                                    "model": model.model.name,
                                    "version": model.model.version,
                                    "location": location,
                                    "sku": sku.name,
                                    "max_capacity": sku.capacity.maximum // 100,
                                    "remaining_capacity": sku.capacity.maximum // 100,
                                }
                            )
    return fetched_quotas_table


def fetch_deployments(client):
    """Fetch the deployments for the specified models in the specified locations.

    Args:
        client (CognitiveServicesManagementClient): The client to use to fetch the deployments.
    """
    deployments_table = []

    for account in client.accounts.list():
        resource_group = account.id.split("/")[4]
        for deployment in client.deployments.list(
            resource_group_name=resource_group,
            account_name=account.name,
        ):
            deployments_table.append(
                {
                    "account": account.name,
                    "location": account.location,
                    "resource_group": resource_group,
                    "deployment": deployment.name,
                    "model": deployment.properties.model.name,
                    "version": deployment.properties.model.version,
                    "used_capacity": deployment.sku.capacity,
                }
            )
    return deployments_table


def main():
    # Fetch the quota for the candidate models in the candidate locations
    print("Fetching quotas for the candidate models in the candidate locations")
    fetched_quotas_table = fetch_quota(client, CANDIDATE_LOCATIONS, CANDIDATE_MODELS)
    # print(json.dumps(fetched_quotas_table, indent=4))

    # Fetch the deployments for the candidate models
    print("Fetching existing deployments in your subscription for the candidate models")
    fetched_deployments_table = fetch_deployments(client)
    # print(json.dumps(fetched_deployments_table, indent=4))

    # substract the capacity of the deployments from the quota
    for quota in fetched_quotas_table:
        for deployment in fetched_deployments_table:
            # capacity is segmented per model per location
            # different model versions are merged into a single model capacity
            if (
                quota["model"] == deployment["model"]
                and quota["location"] == deployment["location"]
            ):
                quota["remaining_capacity"] -= deployment["used_capacity"]

    # show table in a readable markdown format
    print("Model \t\t Version \t Location \t Max Capacity \t Remaining Capacity")
    for quota in fetched_quotas_table:
        print(
            f"{quota['model']} \t\t {quota['version']} \t\t {quota['location']} \t {quota['max_capacity']} \t\t {quota['remaining_capacity']}"
        )


if __name__ == "__main__":
    main()

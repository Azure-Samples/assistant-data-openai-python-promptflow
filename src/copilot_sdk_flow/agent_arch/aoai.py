import os
import logging
from openai import AzureOpenAI, AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from typing import Union
from promptflow.tracing import trace


@trace
def get_azure_openai_client(
    stream: bool = False, azure_endpoint: str = None, api_version: str = None
) -> Union[AzureOpenAI, AsyncAzureOpenAI]:
    """Gets an AzureOpenAI client."""

    # check if the azure_endpoint is provided or in the environment variables
    assert (
        azure_endpoint is not None or "AZURE_OPENAI_ENDPOINT" in os.environ
    ), "azure_endpoint is None, AZURE_OPENAI_ENDPOINT environment variable is required"

    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_API_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        aoai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=api_version
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        )
    else:
        logging.info("Using Azure AD authentification [recommended]")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        aoai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=api_version
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_ad_token_provider=token_provider,
        )
    return aoai_client

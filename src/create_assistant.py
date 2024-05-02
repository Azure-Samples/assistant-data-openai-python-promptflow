"""Creates an OpenAI Assistant with a code interpreter tool and a custom function tool.

You would typically run this script once to create an assistant with the desired tools.
Once the assistant is created, you can interact with it using the OpenAI API (see src/copilot_sdk_flow/chat.py).
"""

import os
import time
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
import logging
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    """Create an assistant with a code interpreter tool and a function tool."""
    logging.basicConfig(level=logging.INFO)

    assert (
        "AZURE_OPENAI_ENDPOINT" in os.environ
    ), "Please set AZURE_OPENAI_ENDPOINT in the environment variables."
    assert (
        "AZURE_OPENAI_CHAT_DEPLOYMENT" in os.environ
    ), "Please set AZURE_OPENAI_CHAT_DEPLOYMENT in the environment variables."

    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        )
    else:
        logging.info("Using Azure AD authentification [recommended]")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_ad_token_provider=token_provider,
        )

    with open(
        os.path.join(
            os.path.dirname(__file__),
            "copilot_sdk_flow",
            "functions",
            "query_order_data.json",
        )
    ) as f:
        custom_function_spec = json.load(f)

    logging.info(f"Creating assistant...")
    assistant = client.beta.assistants.create(
        instructions="You are a helpful data analytics assistant helping user answer questions about the contoso sales data.",
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        tools=[
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": custom_function_spec,
            },
        ],
    )

    print(
        f"""
******************************************************************
Successfully created assistant with id: {assistant.id}.
Create an environment variable
    
    AZURE_OPENAI_ASSISTANT_ID={assistant.id}
    
to use this assistant in your code. Or write it in your .env file.
******************************************************************"""
    )


if __name__ == "__main__":
    main()

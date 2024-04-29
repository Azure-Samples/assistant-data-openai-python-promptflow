import os
from typing import List
from promptflow.core import tool
from promptflow.connections import AzureOpenAIConnection

# local imports
from chat import chat_completion


@tool
def orchestrator(
    # promptflow 'chat' contract
    chat_history: List,
    chat_input: str,
    # parameters for the actual orchestration engine (assistants)
    orchestrator_aoai_connection: AzureOpenAIConnection,
    orchestrator_assistant_id: str,
) -> str:
    # refactor the whole chat_history thing
    conversation = [
        {
            "role": "user" if "inputs" in message else "assistant",
            "content": (
                message["inputs"]["chat_input"]
                if "inputs" in message
                else message["outputs"]["chat_output"]
            ),
        }
        for message in chat_history
    ]

    # add the user input as last message in the conversation
    conversation.append({"role": "user", "content": chat_input})

    # transforming pf connection into env vars for chat_completion
    os.environ["AZURE_OPENAI_ENDPOINT"] = orchestrator_aoai_connection.api_base
    os.environ["AZURE_OPENAI_KEY"] = orchestrator_aoai_connection.api_key
    os.environ["OPENAI_ASSISTANT_ID"] = orchestrator_assistant_id

    # just running the chat_completion function
    completion = chat_completion(conversation)

    assert completion is not None, "chat_completion returned None"

    return completion["choices"][0]["message"]["content"]

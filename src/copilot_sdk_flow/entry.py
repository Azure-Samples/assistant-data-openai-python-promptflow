# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
from typing import TypedDict

# set environment variables before importing any other code
from dotenv import load_dotenv, find_dotenv
import json

print(find_dotenv())
load_dotenv(override=True)


class ChatResponse(TypedDict):
    context: dict
    reply: str


from promptflow.core import tool

# local imports
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))
from chat import chat_completion


# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need
@tool
def flow_entry_copilot_assistants(
    chat_input: str, stream=False, chat_history: list = [], context: str = None
) -> ChatResponse:
    # json parse context as dict
    context = json.loads(context) if context else {}

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

    # Call the async chat function with a single question and print the response
    if stream:
        result = chat_completion(conversation, stream=True, context=context)
        for r in result:
            print(r)
            print("\n")
    else:
        result = chat_completion(conversation, stream=False, context=context)
        print(result)

    return ChatResponse(
        reply=result["choices"][0]["message"]["content"],
        context=result["choices"][0].get("context", ""),
    )

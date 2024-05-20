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

# TODO: using sys.path as hotfix to be able to run the script from 3 different locations
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
    conversation = []
    for message in chat_history:
        if "inputs" in message:
            conversation.append(
                {
                    "role": "user",
                    "content": message["inputs"]["chat_input"],
                }
            )
        elif "outputs" in message:
            conversation.append(
                {
                    "role": "assistant",
                    "content": message["outputs"]["reply"],
                }
            )
        else:
            pass

    # add the user input as last message in the conversation
    conversation.append({"role": "user", "content": chat_input})

    return chat_completion(conversation, stream=stream, context=context)

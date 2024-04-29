# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

# enable type annotation syntax on Python versions earlier than 3.9
from __future__ import annotations

# set environment variables before importing any other code
from dotenv import load_dotenv

load_dotenv()

import asyncio
import platform

from promptflow.core import tool

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need


@tool
def flow_entry_copilot_sdk(question: str, stream=False) -> str:
    # workaround for a bug on windows
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    from chat import chat_completion

    # Call the async chat function with a single question and print the response
    if stream:
        result = asyncio.run(
            chat_completion([{"role": "user", "content": question}], stream=True)
        )
        for r in result:
            print(r)
            print("\n")
    else:
        result = chat_completion([{"role": "user", "content": question}], stream=False)
        # result = asyncio.run(
        #     chat_completion([{"role": "user", "content": question}], stream=False)
        # )
        print(result)
    return result

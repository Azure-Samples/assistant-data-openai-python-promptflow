from typing import List

import os
import logging
import json
import inspect
import base64
import asyncio

from promptflow.tracing import trace

# local imports
import sys

# TODO: using sys.path as hotfix to be able to run the script from 3 different locations
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agent_arch.client import get_azure_openai_client
from agent_arch.config import Configuration
from agent_arch.sessions import SessionManager
from agent_arch.orchestrator import Orchestrator
from agent_arch.extensions.manager import ExtensionsManager


@trace
def chat_completion(
    messages: list[dict],
    stream: bool = False,
    context: dict[str, any] = {},
):
    # a couple basic checks
    if not messages:
        return {"error": "No messages provided."}

    # loads the system config from the environment variables
    # with overrides from the context
    config = Configuration.from_env_and_context(context)

    aoai_client = get_azure_openai_client(stream=False)  # TODO: Assistants Streaming
    session_manager = SessionManager(aoai_client)

    if "session_id" not in context:
        session = session_manager.create_session()
    else:
        session = session_manager.get_session(context.get("session_id"))

    session.record_message(messages[0])
    extensions = ExtensionsManager(config)
    extensions.load()

    orchestrator = Orchestrator(config, aoai_client, session, extensions)
    orchestrator.run_loop()

    def milk_that_queue():
        while session.output_queue:
            yield session.output_queue.popleft()

    return {"reply": milk_that_queue(), "context": context}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # test the chat completion function
    from promptflow.tracing import start_trace

    start_trace()

    import asyncio

    # enable logging with good formatting
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # disable logging for azure.core
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    reply = chat_completion([{"role": "user", "content": "plot avg sales per month"}])[
        "reply"
    ]

    # logging.info("Returned length: %s", len(output_queue))

    for message in reply:
        print(message)
    # while output_queue:
    #     print(output_queue.popleft())
    # for message in iter(output_queue.get, None):
    #     print(message)

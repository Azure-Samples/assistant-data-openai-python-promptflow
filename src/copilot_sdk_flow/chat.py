"""This script contains the main chat completion function used as
an entry point for our demo."""

import os
from promptflow.tracing import trace

# local imports
import sys

# TODO: using sys.path as hotfix to be able to run the script from 3 different locations
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agent_arch.aoai import get_azure_openai_client
from agent_arch.config import Configuration
from agent_arch.sessions import SessionManager
from agent_arch.orchestrator import Orchestrator
from agent_arch.extensions.manager import ExtensionsManager
from agent_arch.event_log import EventLogger
from agent_arch.messages import TextResponse


@trace
def chat_completion(
    messages: list[dict],
    stream: bool = False,
    context: dict[str, any] = {},
):
    event_logger = EventLogger()
    event_logger.start_span(EventLogger.TIME_TO_FIRST_TOKEN)
    event_logger.start_span(EventLogger.TIME_TO_FIRST_EXTENSION_CALL)
    event_logger.start_span(EventLogger.TIME_TO_RUN_LOOP)

    # a couple basic checks
    if not messages:
        return {"error": "No messages provided."}

    # loads the system config from the environment variables
    # with overrides from the context
    config = Configuration.from_env_and_context(context)

    # get the Azure OpenAI client
    aoai_client = get_azure_openai_client(
        stream=False,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_version=config.AZURE_OPENAI_API_VERSION,
    )  # TODO: Assistants Streaming

    # the session manager is responsible for creating and storing sessions
    session_manager = SessionManager(aoai_client, config)

    if "session_id" not in context:
        session = session_manager.create_session()
        context["session_id"] = session.id
        # record all messages so far
        for message in messages:
            session.record_message(message)
    else:
        session = session_manager.get_session(context.get("session_id"))
        # record the user message into the session
        session.record_message(messages[-1])

    # the extension manager is responsible for loading and invoking extensions
    extensions = ExtensionsManager(config)
    extensions.load()

    # the orchestrator is responsible for managing the assistant run
    orchestrator = Orchestrator(config, aoai_client, session, extensions, event_logger)
    try:
        orchestrator.run_loop()
    except Exception as e:
        session.send(TextResponse(role="assistant", content=f"`Error: {e}`"))

    # for now we'll use this trick for outputs
    def output_queue_iterate():
        while session.output_queue:
            yield session.output_queue.popleft()
            event_logger.end_span(EventLogger.TIME_TO_FIRST_TOKEN)

    chat_completion_output = {
        "context": context,
    }
    if context.get("return_spans", False):
        chat_completion_output["context"]["spans"] = event_logger.report()

    if stream:
        chat_completion_output["reply"] = output_queue_iterate()
    else:
        chat_completion_output["reply"] = "".join(list(output_queue_iterate()))
        if chat_completion_output["reply"] == "":
            chat_completion_output["reply"] = "No reply from the assistant."

    return chat_completion_output


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # from promptflow.tracing import start_trace
    # start_trace()

    import logging
    import json

    logging.basicConfig(level=logging.INFO)
    # remove azure.core logging
    logging.getLogger("azure.core").setLevel(logging.ERROR)
    logging.getLogger("azure.identity").setLevel(logging.ERROR)
    # logging.getLogger("httpx").setLevel(logging.ERROR)

    # sample usage
    messages = [
        # {"role": "user", "content": "plot avg monthly sales"},
        {"role": "user", "content": "avg sales in jan"},
    ]
    result = chat_completion(messages, stream=False, context={"return_spans": True})
    print(json.dumps(result, indent=2))

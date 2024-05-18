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

    # get the Azure OpenAI client
    aoai_client = get_azure_openai_client(stream=False)  # TODO: Assistants Streaming

    # the session manager is responsible for creating and storing sessions
    session_manager = SessionManager(aoai_client)

    if "session_id" not in context:
        session = session_manager.create_session()
    else:
        session = session_manager.get_session(context.get("session_id"))

    # record the user message into the session
    session.record_message(messages[0])

    # the extension manager is responsible for loading and invoking extensions
    extensions = ExtensionsManager(config)
    extensions.load()

    # the orchestrator is responsible for managing the assistant run
    orchestrator = Orchestrator(config, aoai_client, session, extensions)
    orchestrator.run_loop()

    # for now we'll use this trick for outputs
    def output_queue_iterate():
        while session.output_queue:
            yield session.output_queue.popleft()

    return {"reply": output_queue_iterate(), "context": context}

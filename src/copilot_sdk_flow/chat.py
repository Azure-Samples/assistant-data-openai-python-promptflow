# enable type annotation syntax on Python versions earlier than 3.9
from __future__ import annotations

import time
import os
import logging
import json

import base64

from openai import AzureOpenAI
from promptflow.tracing import start_trace
from promptflow.tracing import trace
from distutils.util import strtobool

# local imports
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


@trace
def run_assistant_thread(
    client,
    assistant,
    thread,
    max_waiting_time: int = 120,
    tools: dict[str, callable] = {},
):
    # Run the thread
    logging.info("Running the thread")
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    logging.info(f"Pre loop run status: {run.status}")

    start_time = time.time()
    step_logging_cursor = None

    # keep track of messages happening during the loop
    internal_memory = []

    # loop until max_waiting_time is reached
    while (time.time() - start_time) < max_waiting_time:
        # checks the run regularly
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        logging.info(
            f"Run status: {run.status} (time={int(time.time() - start_time)}s, max_waiting_time={max_waiting_time})"
        )

        # check run steps
        run_steps = client.beta.threads.runs.steps.list(
            thread_id=thread.id, run_id=run.id, after=step_logging_cursor
        )
        for step in run_steps:
            logging.info("The assistant has moved forward to step {}".format(step.id))
            internal_memory.append(step.step_details.model_dump())
            step_logging_cursor = step.id

        if run.status == "completed":
            messages = []
            for message in client.beta.threads.messages.list(thread_id=thread.id):
                message = client.beta.threads.messages.retrieve(
                    thread_id=thread.id, message_id=message.id
                )
                messages.append(message)
            logging.info(f"Run completed with {len(messages)} messages.")
            final_message = messages[0]

            text_response = "\n".join(
                [
                    message.text.value
                    for message in final_message.content
                    if message.type == "text"
                ]
            )
            file_ids = []
            for entry in final_message.content:
                if entry.type == "image_file":
                    file_ids.append(entry.image_file.file_id)
                else:
                    logging.critical("Unknown content type: {}".format(entry.type))
            files = [
                {
                    "file_id": file_id,
                    "type": "image",
                    "content": base64.b64encode(
                        client.files.content(file_id).read()
                    ).decode("utf-8"),
                }
                for file_id in file_ids
            ]
            # print(files)

            # render something that pass for a ChatCompletion object
            ret_val = {
                "id": final_message.id,
                "model": "openai/assistants",
                "created": final_message.created_at,
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": text_response,
                            "files": files,
                        },
                        "context": {
                            "thread_id": thread.id,
                            "steps": internal_memory,
                        },
                    }
                ],
            }

            return ret_val
        elif run.status == "requires_action":
            # if the run requires us to run a tool
            tool_call_outputs = []

            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                internal_memory.append(tool_call.model_dump())
                if tool_call.type == "function":
                    tool_func = tools[tool_call.function.name]
                    tool_call_output = tool_func(
                        **json.loads(tool_call.function.arguments)
                    )
                    # tool_call_output = call_tool(
                    #     tools_map[tool_call.function.name], **json.loads(tool_call.function.arguments)
                    # )
                    tool_call_outputs.append(
                        {
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(tool_call_output),
                        }
                    )
                    internal_memory.append(tool_call_outputs[-1])
                else:
                    raise ValueError(f"Unsupported tool call type: {tool_call.type}")

            if tool_call_outputs:
                _ = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=tool_call_outputs,
                )
        elif run.status in ["cancelled", "expired", "failed"]:
            raise ValueError(f"Run failed with status: {run.status}")

        elif run.status in ["in_progress", "queued"]:
            time.sleep(1)

        else:
            raise ValueError(f"Unknown run status: {run.status}")


@trace
def chat_completion(
    messages: list[dict],
    stream: bool = False,
    session_state: any = None,
    context: dict[str, any] = {},
):
    # a couple basic checks
    if not messages:
        return {"error": "No messages provided."}

    # verify required env vars
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "OPENAI_ASSISTANT_ID",
    ]
    missing_env_vars = []
    for env_var in required_env_vars:
        if env_var not in os.environ:
            missing_env_vars.append(env_var)
    assert not missing_env_vars, f"Missing environment variables: {missing_env_vars}"

    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        aoai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
        )
    else:
        logging.info("Using Azure AD authentification [recommended]")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        aoai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2024-02-15-preview",
            azure_ad_token_provider=token_provider,
        )

    # Get parameters from the context
    if "max_waiting_time" in context:
        logging.info(
            f"Using max_waiting_time from context: {context['max_waiting_time']}"
        )
        max_waiting_time = context["max_waiting_time"]
    else:
        max_waiting_time = 120

    # Get the assistant from the environment variables
    logging.info(
        f"Using assistant_id from environment variables: {os.getenv('OPENAI_ASSISTANT_ID')}"
    )
    assistant = aoai_client.beta.assistants.retrieve(os.getenv("OPENAI_ASSISTANT_ID"))

    # Catch up with a pre-existing thread (id given in the context)
    if "thread_id" in context:
        logging.info(f"Using thread_id from context: {context['thread_id']}")
        thread = aoai_client.beta.threads.retrieve(context["thread_id"])
    else:
        logging.info(f"Creating a new thread")
        thread = aoai_client.beta.threads.create()

    # # Add conversation history in the thread
    # logging.info("Adding conversation history in the thread")
    # for message in messages:
    #     if message["role"] == 'user':
    #         _ = self.client.beta.threads.messages.create(
    #             thread_id=self.thread.id, role=message["role"], content=message["content"]
    #         )

    # Add last message in the thread
    logging.info("Adding last message in the thread")
    _ = aoai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role=messages[-1]["role"],
        content=messages[-1]["content"],
    )

    return run_assistant_thread(
        client=aoai_client,
        assistant=assistant,
        thread=thread,
        max_waiting_time=max_waiting_time,
        tools={},
    )


def _test():
    """Test the chat completion function."""
    # try a functions combo (without RAG)
    response = chat_completion(
        messages=[
            {
                "role": "user",
                "content": "What are the columns in the dataset?",
            }
        ],
    )

    # test expected format
    from openai.types.chat import ChatCompletion

    print(ChatCompletion.model_validate(response))


if __name__ == "__main__":
    # if we run this script locally for testing
    from dotenv import load_dotenv
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="Path to .env file", default=".env")
    parser.add_argument(
        "--log",
        help="Logging level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = parser.parse_args()

    # turn on logging
    logging.basicConfig(
        level=args.log, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # load environment variables
    logging.debug("Loading environment variables from {}".format(args.env))
    load_dotenv(args.env, override=True)

    if strtobool(os.getenv("ENABLE_TRACING") or "False"):
        logging.warning("Enabling tracing for local code execution (chat.py)")
        start_trace()

    _test()

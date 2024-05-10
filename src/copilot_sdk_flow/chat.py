from typing import List

import time
import os
import logging
import json
import inspect
import base64
import asyncio

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from promptflow.tracing import trace

# local imports
import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))
from functions.query_order_data import query_order_data


@trace
async def call_tool(tool_call, message_history: List, output_stream=None):
    available_functions = {
        "query_order_data": query_order_data
    }  # only one function in this example, but you can have multiple

    function_name = tool_call.function.name
    if function_name not in available_functions:
        return {"error": f"Function {function_name} not found."}

    function_to_call = available_functions[function_name]
    try:
        function_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return {"error": f"Error decoding function arguments: {e}"}

    if output_stream:
        await output_stream.send(
            f"calling tool {function_name} with args {function_args}\n"
        )

    function_response = function_to_call(**function_args)
    if inspect.iscoroutinefunction(function_to_call):
        function_response = await function_response

    return function_response


class AssistantThreadRunner(object):
    def __init__(self, client, assistant, thread, max_waiting_time: int = 120):
        self.client = client
        self.assistant = assistant
        self.thread = thread
        self.max_waiting_time = max_waiting_time
        self.run = None
        self.step_logging_cursor = None
        self.messages_during_loop = []
        self.last_message_id = None

    @trace
    def run_loop(self, run):
        self.run = run

        # BONUS: show pre-existing messages in the thread as trace
        self.last_message_id = None
        for message in self.client.beta.threads.messages.list(
            thread_id=self.thread.id, order="asc"
        ):
            _ = trace(self.client.beta.threads.messages.retrieve)(
                thread_id=self.thread.id, message_id=message.id
            )
            self.last_message_id = message.id

        start_time = time.time()
        self.step_logging_cursor = None

        # keep track of messages happening during the loop
        self.messages_during_loop = []

        # loop until max_waiting_time is reached
        while (time.time() - start_time) < self.max_waiting_time:
            # checks the run regularly
            self.run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id, run_id=self.run.id
            )
            logging.info(
                f"Run status: {self.run.status} (time={int(time.time() - start_time)}s, max_waiting_time={self.max_waiting_time})"
            )

            if self.run.status == "completed":
                return self.completed()
            elif self.run.status == "requires_action":
                self.requires_action()
            elif self.run.status in ["cancelled", "expired", "failed"]:
                raise ValueError(f"Run failed with status: {self.run.status}")
            elif self.run.status in ["in_progress", "queued"]:
                time.sleep(0.25)
            else:
                raise ValueError(f"Unknown run status: {self.run.status}")

    @trace
    def completed(self):
        """What to do when run.status == 'completed'"""
        messages = []
        for message in self.client.beta.threads.messages.list(
            thread_id=self.thread.id, order="asc", after=self.last_message_id
        ):
            message = trace(self.client.beta.threads.messages.retrieve)(
                thread_id=self.thread.id, message_id=message.id
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
                    self.client.files.content(file_id).read()
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
                        "thread_id": self.thread.id,
                        # "steps": self.messages_during_loop,
                    },
                }
            ],
        }

        return ret_val

    @trace
    def requires_action(self):
        """What to do when run.status == 'requires_action'"""
        # if the run requires us to run a tool
        tool_call_outputs = []

        for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
            self.messages_during_loop.append(tool_call.model_dump())
            if tool_call.type == "function":
                # let's keep sync for now
                logging.info(
                    f"Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}"
                )
                tool_call_output = asyncio.run(
                    call_tool(tool_call, self.messages_during_loop)
                )
                tool_call_outputs.append(
                    {
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(tool_call_output),
                    }
                )
            else:
                raise ValueError(f"Unsupported tool call type: {tool_call.type}")

        if tool_call_outputs:
            logging.info(f"Submitting tool outputs: {tool_call_outputs}")
            _ = trace(self.client.beta.threads.runs.submit_tool_outputs)(
                thread_id=self.thread.id,
                run_id=self.run.id,
                tool_outputs=tool_call_outputs,
            )


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
        "AZURE_OPENAI_ASSISTANT_ID",
    ]
    missing_env_vars = []
    for env_var in required_env_vars:
        if env_var not in os.environ:
            missing_env_vars.append(env_var)
    assert not missing_env_vars, f"Missing environment variables: {missing_env_vars}"

    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_API_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        aoai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
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
        f"Using assistant_id from environment variables: {os.getenv('AZURE_OPENAI_ASSISTANT_ID')}"
    )
    assistant = trace(aoai_client.beta.assistants.retrieve)(
        os.getenv("AZURE_OPENAI_ASSISTANT_ID")
    )

    # Catch up with a pre-existing thread (id given in the context)
    if "thread_id" in context:
        logging.info(f"Using thread_id from context: {context['thread_id']}")
        thread = trace(aoai_client.beta.threads.retrieve)(context["thread_id"])

        # Add last message in the thread
        logging.info("Adding last message in the thread")
        _ = trace(aoai_client.beta.threads.messages.create)(
            thread_id=thread.id,
            role=messages[-1]["role"],
            content=messages[-1]["content"],
        )
    else:
        logging.info(f"Creating a new thread")
        thread = trace(aoai_client.beta.threads.create)()

        # Add all messages in the thread
        logging.info("Adding all messages in the thread")
        for message in messages:
            _ = trace(aoai_client.beta.threads.messages.create)(
                thread_id=thread.id,
                role=message["role"],
                content=message["content"],
            )

    # Create a run in the thread
    logging.info("Creating the run")
    run = trace(aoai_client.beta.threads.runs.create)(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    logging.info(f"Pre loop run status: {run.status}")

    runner = AssistantThreadRunner(
        client=aoai_client,
        assistant=assistant,
        thread=thread,
        max_waiting_time=max_waiting_time,
    )
    return runner.run_loop(run)

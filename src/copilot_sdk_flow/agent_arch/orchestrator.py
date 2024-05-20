import time
import logging
import json
import base64

from promptflow.tracing import trace

# local imports
from agent_arch.config import Configuration
from agent_arch.messages import (
    TextResponse,
    ImageResponse,
    ExtensionCallMessage,
    ExtensionReturnMessage,
    StepNotification,
)


class Orchestrator:
    def __init__(self, config: Configuration, client, session, extensions):
        self.client = client
        self.config = config
        self.session = session
        self.extensions = extensions

        # getting the Assistant API specific constructs
        logging.info(
            f"Retrieving assistant with id: {config.AZURE_OPENAI_ASSISTANT_ID}"
        )
        self.assistant = trace(self.client.beta.assistants.retrieve)(
            self.config.AZURE_OPENAI_ASSISTANT_ID
        )
        self.thread = self.session.thread

        logging.info(f"Orchestrator initialized with session_id: {session.id}")

        self.run = None
        self.last_step_id = None
        self.last_message_id = None

    @trace
    def run_loop(self):
        logging.info(f"Creating the run")
        self.run = trace(self.client.beta.threads.runs.create)(
            thread_id=self.thread.id, assistant_id=self.assistant.id
        )
        logging.info(f"Pre loop run status: {self.run.status}")

        start_time = time.time()

        # loop until max_waiting_time is reached
        while (time.time() - start_time) < self.config.ORCHESTRATOR_MAX_WAITING_TIME:
            # checks the run regularly
            self.run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id, run_id=self.run.id
            )
            logging.info(
                f"Run status: {self.run.status} (time={int(time.time() - start_time)}s, max_waiting_time={self.config.ORCHESTRATOR_MAX_WAITING_TIME})"
            )

            # check if a step has been completed
            self._check_steps()

            # check if there are messages
            self._check_messages()

            if self.run.status == "completed":
                logging.info(f"Run completed.")
                return self.completed()
            elif self.run.status == "requires_action":
                logging.info(f"Run requires action.")
                self.requires_action()
            elif self.run.status == "cancelled":
                raise Exception(f"Run was cancelled: {self.run.status}")
            elif self.run.status == "expired":
                raise Exception(f"Run expired: {self.run.status}")
            elif self.run.status == "failed":
                raise ValueError(
                    f"Run failed with status: {self.run.status}, last_error: {self.run.last_error}"
                )
            elif self.run.status in ["in_progress", "queued"]:
                time.sleep(0.25)
            else:
                raise ValueError(f"Unknown run status: {self.run.status}")

    @trace
    def _check_messages(self):
        # check if there are messages
        for message in self.client.beta.threads.messages.list(
            thread_id=self.thread.id, order="asc", after=self.last_message_id
        ):
            message = trace(self.client.beta.threads.messages.retrieve)(
                thread_id=self.thread.id, message_id=message.id
            )
            self._process_message(message)
            # self.session.send(message)
            self.last_message_id = message.id

    @trace
    def _process_message(self, message):
        for entry in message.content:
            if message.role == "user":
                # this means a message we just added
                pass
            elif entry.type == "text":
                self.session.send(
                    TextResponse(role=message.role, content=entry.text.value)
                )
            elif entry.type == "image_file":
                file_id = entry.image_file.file_id
                self.session.send(
                    ImageResponse.from_bytes(self.client.files.content(file_id).read())
                )
            else:
                logging.critical("Unknown content type: {}".format(entry.type))

    @trace
    def _check_steps(self):
        """Check if there are new steps to process"""
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread.id, run_id=self.run.id, after=self.last_step_id
        )
        for step in run_steps:
            if step.status == "completed":
                logging.info(
                    "The assistant has moved forward to step {}".format(step.id)
                )
                self._process_completed_step(step)
                self.last_step_id = step.id

    @trace
    def _process_completed_step(self, step):
        """Process a step from the run"""
        if step.type == "tool_calls":
            for tool_call in step.step_details.tool_calls:
                if tool_call.type == "code":
                    self.session.send(
                        StepNotification(
                            type=step.type, content=str(tool_call.model_dump())
                        )
                    )
                elif tool_call.type == "function":
                    self.session.send(
                        StepNotification(
                            type=step.type, content=str(tool_call.model_dump())
                        )
                    )
                else:
                    logging.error(f"Unsupported tool call type: {tool_call.type}")
        else:
            logging.error(f"Unsupported step type: {step.type}")

    @trace
    def completed(self):
        """What to do when run.status == 'completed'"""
        self._check_steps()
        self._check_messages()
        self.session.close()

    @trace
    def requires_action(self):
        """What to do when run.status == 'requires_action'"""
        # if the run requires us to run a tool
        tool_call_outputs = []

        for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.type == "function":
                # let's keep sync for now
                logging.info(
                    f"Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}"
                )
                # decode the arguments from the api
                try:
                    extension_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logging.critical(f"Error decoding extension arguments: {e}")
                    continue

                # send some early message to the user
                self.session.send(
                    ExtensionCallMessage(
                        name=tool_call.function.name, args=extension_args
                    )
                )

                # invoke the extension
                tool_call_output = self.extensions.get_extension(
                    tool_call.function.name
                ).invoke(**extension_args)

                # send success to the user
                self.session.send(
                    ExtensionReturnMessage(
                        name=tool_call.function.name, content=tool_call_output
                    )
                )

                # store the output for the tool
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

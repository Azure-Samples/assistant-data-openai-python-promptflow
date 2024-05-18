from typing import Union
import logging
from openai import AzureOpenAI
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.beta.thread import Thread
import traceback
from typing import Any
from promptflow.tracing import trace
from collections import deque
from agent_arch.messages import (
    ExtensionCallMessage,
    ExtensionReturnMessage,
    StepNotification,
    TextResponse,
    ImageResponse,
)


class Session:
    """Represents a session with the assistant."""

    def __init__(self, thread: Thread, client: AzureOpenAI):
        """Initializes a new session with the assistant.

        Args:
            thread (Thread): The thread associated with the session.
            client (AzureOpenAI): The AzureOpenAI client.
        """
        self.id = thread.id
        self.thread = thread
        self.client = client
        self.output_queue = deque()
        self.open = True

    @trace
    def record_message(self, message: Union[dict, ChatCompletionMessage]):
        """Appends a message to the session.

        Args:
            message (ChatCompletionMessage): The message to append.

        Returns:
            None
        """
        if isinstance(message, dict):
            assert "role" in message, "role is required"
            assert "content" in message, "content is required"
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role=message["role"],
                content=message["content"],
            )
        elif isinstance(message, ChatCompletionMessage):
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role=message.role,
                content=message.content,
            )

    @trace
    def send(self, message: Any):
        """Sends a message back to the user.

        Args:
            message (Any): The message to send.
        """
        if isinstance(message, ExtensionCallMessage):
            if message.name == "query_order_data":
                output_message = f"_Calling extension `{message.name}` with SQL query:_\n```sql\n{message.args['sql_query']}\n```\n\n"
            else:
                output_message = f"_Calling extension `{message.name}`_\n\n"
        elif isinstance(message, ExtensionReturnMessage):
            # output_message = f"_Extension `{message.name}` returned: `{message.content}`_\n\n"
            output_message = None
        elif isinstance(message, StepNotification):
            # output_message = f"_Agent moved forward with step: `{message.type}`: `{message.content}`_\n"
            output_message = None
        elif isinstance(message, TextResponse):
            output_message = message.content
        elif isinstance(message, ImageResponse):
            output_message = "![image](" + message.content + ")\n\n"
        else:
            logging.critical(f"Unknown message type: {type(message)}")
            output_message = f"`Unknown message type: {type(message)}`\n\n"
        if output_message:
            logging.info(
                f"Queueing message type={message.__class__.__name__} len={len(output_message)}"
            )
            self.output_queue.append(output_message)

    def close(self):
        """Closes the session."""
        self.open = False


class SessionManager:
    """Manages assistant sessions."""

    def __init__(self, aoai_client: AzureOpenAI):
        """Initializes a new session manager.

        Args:
            aoai_client (AzureOpenAI): The AzureOpenAI client.
        """
        self.aoai_client = aoai_client
        self.sessions = {}

    @trace
    def create_session(self) -> Session:
        """Creates a new session."""
        thread = self.aoai_client.beta.threads.create()
        return Session(thread=thread, client=self.aoai_client)

    @trace
    def get_session(self, session_id: str) -> Union[Session, None]:
        """Gets a session by its ID."""
        if session_id in self.sessions:
            return self.sessions[session_id]

        try:
            thread = self.aoai_client.beta.threads.retrieve(session_id)
        except Exception as e:
            logging.critical(
                f"Error retrieving thread {session_id}: {traceback.format_exc()}"
            )
            return None

        self.sessions[thread.id] = Session(
            assistant_id=thread.assistant_id,
            thread_id=thread.id,
        )
        return self.sessions[thread.id]

    def set_session(self, session_id, session: Session):
        """Sets a session."""
        self.sessions[session_id] = session

    def clear_session(self, session_id):
        """Clears a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

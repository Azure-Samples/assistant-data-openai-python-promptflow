import os
import inspect
import json
from promptflow.tracing import trace
from agent_arch.sessions import AssistantSession
from agent_arch.messages import ExtensionCallMessage, ExtensionReturnMessage
from typing import List
import asyncio


class Extension:
    def __init__(self, name, function):
        self.name = name
        self.function = function

    @trace
    def invoke(self, arguments_json: str):
        try:
            function_args = json.loads(arguments_json)
        except json.JSONDecodeError as e:
            return {"error": f"Error decoding function arguments: {e}"}

        function_response = asyncio.run(self.function(**function_args))
        # if inspect.iscoroutinefunction(self.function):
        #     function_response = await function_response

        return function_response


class ExtensionsManager:
    def __init__(self, config):
        self.extensions = {}

    def load(self):
        from .query_order_data import query_order_data

        self.extensions["query_order_data"] = Extension(
            name="query_order_data",
            function=query_order_data,
        )

    def get_extension(self, name):
        return self.extensions.get(name, None)

"""In the context of our demo, Extensions are functions that can be invoked by the assistant.
The ExtensionsManager class manages those extensions for the Orchestrator."""

import os
import inspect
import json
from promptflow.tracing import trace
from typing import Any
import asyncio
import inspect


class Extension:
    """Represents an extension that can be invoked by the assistant."""

    def __init__(self, name, function):
        self.name = name
        self.function = function

    @trace
    def invoke(self, **extension_args) -> Any:
        """Invokes the extension with the provided arguments.

        Args:
            **extension_args: The arguments to pass to the extension.

        Returns:
            Any: The response from the extension.
        """
        # test if the function is async
        if inspect.iscoroutinefunction(self.function):
            function_response = asyncio.run(self.function(**extension_args))
        else:
            function_response = self.function(**extension_args)

        return function_response


class ExtensionsManager:
    """Manages the extensions that can be invoked by the system."""

    def __init__(self, config):
        self.extensions = {}

    def load(self):
        """Loads the extensions into the manager."""
        from .query_order_data import query_order_data

        self.extensions["query_order_data"] = Extension(
            name="query_order_data",
            function=query_order_data,
        )

    def get_extension(self, name: str) -> Extension:
        """Gets an extension by its name."""
        return self.extensions.get(name, None)

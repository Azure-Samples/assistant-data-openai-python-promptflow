import os
from dataclasses import dataclass
from typing import Optional
from typing import Dict
from pydantic import BaseModel
from distutils.util import strtobool


class Configuration(BaseModel):
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_ASSISTANT_ID: str
    ORCHESTRATOR_MAX_WAITING_TIME: int = 60
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = "2024-05-01-preview"
    COMPLETION_INSERT_NOTIFICATIONS: Optional[bool] = False

    @classmethod
    def from_env_and_context(cls, context: Dict[str, str]):
        # verify required env vars
        required_env_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_ASSISTANT_ID",
        ]
        missing_env_vars = []
        for env_var in required_env_vars:
            if env_var not in os.environ:
                missing_env_vars.append(env_var)
        assert (
            not missing_env_vars
        ), f"Missing environment variables: {missing_env_vars}"

        return cls(
            AZURE_OPENAI_ENDPOINT=os.environ["AZURE_OPENAI_ENDPOINT"],
            AZURE_OPENAI_ASSISTANT_ID=context.get("AZURE_OPENAI_ASSISTANT_ID")
            or os.environ["AZURE_OPENAI_ASSISTANT_ID"],
            ORCHESTRATOR_MAX_WAITING_TIME=int(
                context.get("ORCHESTRATOR_MAX_WAITING_TIME")
                or os.getenv("ORCHESTRATOR_MAX_WAITING_TIME")
                or "60"
            ),
            AZURE_OPENAI_API_KEY=os.getenv("AZURE_OPENAI_API_KEY"),
            AZURE_OPENAI_API_VERSION=os.getenv(
                "AZURE_OPENAI_API_VERSION", "2024-05-01-preview"
            ),
            COMPLETION_INSERT_NOTIFICATIONS=strtobool(
                os.getenv("COMPLETION_INSERT_NOTIFICATIONS", "False")
            ),
        )

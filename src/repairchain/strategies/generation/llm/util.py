from __future__ import annotations

__all__ = ("Util",)

import typing as t
from dataclasses import dataclass, field

import tiktoken
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis

# Define the composite message type
MessageType = (ChatCompletionSystemMessageParam |
               ChatCompletionUserMessageParam |
               ChatCompletionAssistantMessageParam |
               ChatCompletionToolMessageParam |
               ChatCompletionFunctionMessageParam)

# Define the iterable of the composite message type
MessagesIterable = list[MessageType]


@dataclass
class Util:
    retry_attempts: int = field(default=5)
    short_sleep: int = field(default=5)
    long_sleep: int = field(default=30)
    context_size: int = field(default=50000)

    @staticmethod
    def implied_functions_to_str(diagnosis: Diagnosis) -> list[str]:
        return [function_diagnosis.name for function_diagnosis in diagnosis.implicated_functions_at_head]

    @staticmethod
    def count_tokens(text: str, model: str = "oai-gpt-4o") -> int:
        try:
            # Explicitly use the cl100k_base encoder
            encoding = tiktoken.get_encoding("cl100k_base")
        except KeyError as e:
            error_message = f"Failed to get encoding for the model {model}."
            raise ValueError(error_message) from e

        tokens = encoding.encode(text)
        return len(tokens)

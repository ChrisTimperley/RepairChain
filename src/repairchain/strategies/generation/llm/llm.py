from __future__ import annotations

import os
import time
import typing as t
from dataclasses import dataclass

import openai
from loguru import logger

from repairchain.strategies.generation.llm.util import Util

if t.TYPE_CHECKING:
    from repairchain.strategies.generation.llm.util import MessagesIterable


@dataclass
class LLM:
    model: str
    litellm_url: str | None
    master_key: str | None

    def __init__(self, model: str = "oai-gpt-4o", litellm_url: str | None = os.getenv("AIXCC_LITELLM_HOSTNAME"),
                 master_key: str | None = os.getenv("LITELLM_KEY")) -> None:
        self.model = model
        if litellm_url is None:
            self.litellm_url = "http://0.0.0.0:4000"
            logger.info(f"litellm_url has no OS environment variable. Defaulting to {self.litellm_url}")
        else:
            self.litellm_url = litellm_url

        if master_key is None:
            self.master_key = "sk-1234"
            logger.info(f"master_key has no OS environment variable. Defaulting to {self.master_key}")
        else:
            self.master_key = master_key

    def _call_llm_json(self, messages: MessagesIterable) -> str:
        model = self.model
        client = openai.OpenAI(
            api_key=self.master_key,
            base_url=self.litellm_url,
        )

        retry_attempts = Util.retry_attempts
        for attempt in range(retry_attempts):
            try:
                response = client.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=messages,
                )

                llm_output = response.choices[0].message.content
                if llm_output is None:
                    return ""
                return llm_output

            except openai.APITimeoutError as e:
                logger.info(f"API timeout error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.InternalServerError as e:
                logger.info(f"Internal server error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.RateLimitError as e:
                logger.info(f"Rate limit error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.long_sleep)  # wait longer before retrying
            except openai.UnprocessableEntityError as e:
                logger.info(f"Unprocessable entity error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.OpenAIError as e:
                logger.info(f"General OpenAI API error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            else:
                # unreachable code but makes the linter happy
                return ""

        return ""

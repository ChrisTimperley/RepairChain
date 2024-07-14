from __future__ import annotations

import time
import typing as t
from dataclasses import dataclass

import openai
from loguru import logger

from repairchain.strategies.generation.llm.util import Util

if t.TYPE_CHECKING:
    from repairchain.models.settings import Settings
    from repairchain.strategies.generation.llm.util import MessagesIterable


@dataclass
class LLM:
    model: str
    litellm_url: str | None
    master_key: str | None

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        model: str | None = None,
    ) -> t.Self:
        if model is None:
            model = settings.litellm_model
        return cls(
            model=model,
            litellm_url=settings.litellm_url,
            master_key=settings.litellm_key,
        )

    def _simple_call_llm(self, messages: MessagesIterable) -> str | None:
        logger.info(f"Calling LLM with model={self.model}")
        model = self.model
        client = openai.OpenAI(
            api_key=self.master_key,
            base_url=self.litellm_url,
        )

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        retry_attempts = Util.retry_attempts
        for attempt in range(retry_attempts):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                )

                llm_output = response.choices[0].message.content
                if llm_output is None:
                    return None
                return llm_output

            except openai.APITimeoutError as e:
                logger.warning(f"API timeout error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.InternalServerError as e:
                logger.warning(f"Internal server error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.long_sleep)  # wait longer before retrying
            except openai.UnprocessableEntityError as e:
                logger.warning(f"Unprocessable entity error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.OpenAIError as e:
                # do not retry in this case
                logger.warning(f"General OpenAI API error: {e}.")
                return None

        return None

    def _call_llm_json(self, messages: MessagesIterable) -> str | None:
        logger.info(f"Calling LLM with model={self.model}")
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
                    return None
                return llm_output

            except openai.APITimeoutError as e:
                logger.warning(f"API timeout error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.InternalServerError as e:
                logger.warning(f"Internal server error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.long_sleep)  # wait longer before retrying
            except openai.UnprocessableEntityError as e:
                logger.warning(f"Unprocessable entity error: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                time.sleep(Util.short_sleep)  # brief wait before retrying
            except openai.OpenAIError as e:
                # do not retry in this case
                logger.warning(f"General OpenAI API error: {e}.")
                return None

        return None

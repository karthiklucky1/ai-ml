# backend/llm/openai_client.py
from __future__ import annotations
import os
from typing import Optional, Any, Dict

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore


class LLMError(Exception):
    pass


class OpenAITextClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        if OpenAI is None:
            raise LLMError(
                "openai package not installed. Run: pip install openai")

        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not key:
            raise LLMError("OPENAI_API_KEY not set.")

        # Guard against copy/paste mistakes like smart quotes or "Bearer ...".
        key = key.replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
        key = key.strip("'\"")
        if key.lower().startswith("bearer "):
            key = key[7:].strip()

        try:
            key.encode("ascii")
        except UnicodeEncodeError as e:
            raise LLMError(
                "OPENAI_API_KEY contains non-ASCII characters. Remove quotes/smart quotes and keep only the raw key."
            ) from e

        self.client = OpenAI(api_key=key)
        self.model = model

    def complete_json(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 700) -> Dict[str, Any]:
        """
        Forces valid JSON output using response_format=json_object
        """
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},  # key fix
            )
            content = resp.choices[0].message.content or "{}"
            import json
            return json.loads(content)
        except Exception as e:
            raise LLMError(str(e)) from e

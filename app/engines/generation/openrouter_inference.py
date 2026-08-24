"""
OpenRouter Generation Engine
----------------------------
OpenRouter exposes an OpenAI-compatible Chat Completions API at
https://openrouter.ai/api/v1  so we use the openai package pointed at
that base URL.  Free models (suffix ``:free``) require no billing.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.utils.config import settings


class OpenRouterInference:
    """
    Generation engine backed by the OpenRouter API.

    Default model: ``mistralai/mistral-7b-instruct:free``  (always free).
    Any model listed on https://openrouter.ai/models can be used.
    """

    DEFAULT_MODEL = "mistralai/mistral-7b-instruct:free"
    API_BASE = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model or self.DEFAULT_MODEL
        self.api_base = settings.openrouter_api_url or self.API_BASE
        self.offline_mode = not bool(self.api_key)
        self._client = None
        self._new_api = False

        if not self.offline_mode:
            self._init_client()

    def _init_client(self) -> None:
        try:
            import openai as _oa

            # openai >= 1.0 has OpenAI class with base_url param
            if hasattr(_oa, "OpenAI"):
                self._client = _oa.OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )
                self._new_api = True
            else:
                # Legacy v0/v3 — set module-level globals
                _oa.api_key = self.api_key
                _oa.api_base = self.api_base
                self._client = _oa
                self._new_api = False
        except ImportError:
            print(
                "WARNING: openai package not installed — "
                "run `pip install openai`. Falling back to offline mode.",
                flush=True,
            )
            self.offline_mode = True

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        if self.offline_mode:
            return self._offline_response(prompt)

        messages = [{"role": "user", "content": prompt}]
        return self._chat(messages, max_tokens, temperature, top_p, timeout)

    def generate_with_context(
        self,
        query: str,
        context: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        template: Optional[str] = None,
        timeout: int = 60,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        if self.offline_mode:
            return self._offline_response(query)

        if template:
            try:
                filled = template.format(query=query, context=context)
            except (KeyError, IndexError):
                filled = template
            messages = [{"role": "user", "content": filled}]
        else:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. Answer the user's question "
                        "using only the provided context. "
                        "If the context does not contain enough information, say so."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:",
                },
            ]

        result = self._chat(messages, max_tokens, temperature, top_p, timeout)
        result["query"] = query
        return result

    def generate_batch(
        self,
        prompts: List[str],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> List[Dict[str, Any]]:
        return [
            self.generate(p, max_tokens=max_tokens, temperature=temperature)
            for p in prompts
        ]

    # ------------------------------------------------------------------
    # Internal dispatcher
    # ------------------------------------------------------------------

    def _chat(
        self,
        messages: list,
        max_tokens: int,
        temperature: float,
        top_p: float,
        timeout: int,
    ) -> Dict[str, Any]:
        try:
            start = time.time()

            if self._new_api:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    timeout=timeout,
                    extra_headers={
                        "HTTP-Referer": "https://microbrain.local",
                        "X-Title": "MicroBrain RAG",
                    },
                )
                elapsed_ms = int((time.time() - start) * 1000)
                generated = response.choices[0].message.content or ""
                usage = response.usage
                return {
                    "generated_text": generated,
                    "model": self.model,
                    "tokens_used": usage.total_tokens if usage else len(generated.split()),
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "generation_time_ms": elapsed_ms,
                }
            else:
                # Legacy v0/v3
                import openai as _oa
                _oa.api_key = self.api_key
                _oa.api_base = self.api_base
                response = _oa.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    request_timeout=timeout,
                    headers={
                        "HTTP-Referer": "https://microbrain.local",
                        "X-Title": "MicroBrain RAG",
                    },
                )
                elapsed_ms = int((time.time() - start) * 1000)
                generated = response["choices"][0]["message"]["content"] or ""
                usage = response.get("usage", {})
                return {
                    "generated_text": generated,
                    "model": self.model,
                    "tokens_used": usage.get("total_tokens", len(generated.split())),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "generation_time_ms": elapsed_ms,
                }

        except Exception as exc:
            print(
                f"WARNING: OpenRouter call failed — {exc}. Using offline fallback.",
                flush=True,
            )
            result = self._offline_response(messages[-1]["content"])
            result["error"] = str(exc)
            return result

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _offline_response(self, prompt: str) -> Dict[str, Any]:
        lower = prompt.lower()
        if "context:" in lower and ("question:" in lower or "answer:" in lower):
            ctx_start = lower.find("context:") + len("context:")
            end = min(
                lower.find("question:") if "question:" in lower else len(prompt),
                lower.find("answer:") if "answer:" in lower else len(prompt),
            )
            ctx_text = prompt[ctx_start:end].strip()
            sentences = [s.strip() for s in ctx_text.replace("\n", " ").split(".") if s.strip()]
            answer = ". ".join(sentences[:2]) or ctx_text[:400]
        else:
            answer = prompt[:400]
        return {
            "generated_text": answer,
            "model": self.model,
            "tokens_used": len(answer.split()),
            "offline_mode": True,
        }

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openrouter",
            "model": self.model,
            "api_base": self.api_base,
            "offline_mode": self.offline_mode,
        }

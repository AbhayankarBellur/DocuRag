"""OpenAI Chat Completion Generation Engine"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.utils.config import settings


class OpenAIInference:
    """
    OpenAI Chat Completions API for RAG-style text generation.

    Uses ``gpt-4o-mini`` by default — cheap, fast, and accurate enough for
    retrieval-augmented answer synthesis.  Switch to ``gpt-4o`` for higher
    quality at higher cost.

    Falls back gracefully to an offline stub when no API key is configured.
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or self.DEFAULT_MODEL
        self.offline_mode = not bool(self.api_key)
        self._client = None  # lazy-init

        if not self.offline_mode:
            self._init_client()

    def _init_client(self) -> None:
        try:
            import openai as _openai
            self._openai = _openai
            # openai v0/v1/v3 all expose openai.api_key at module level
            _openai.api_key = self.api_key
            self._client = _openai  # module itself is the client for v0/v3
            # Detect if the new (>=1.0) client class is available
            if hasattr(_openai, "OpenAI"):
                self._client = _openai.OpenAI(api_key=self.api_key)
                self._new_api = True
            else:
                self._new_api = False
        except ImportError:
            print(
                "WARNING: openai package not installed — "
                "run `pip install openai`.  Falling back to offline mode.",
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
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate a completion for the given prompt.

        The prompt is sent as a single ``user`` message.  For RAG use cases
        prefer :meth:`generate_with_context` which builds a proper
        system + user message pair.
        """
        if self.offline_mode:
            return self._offline_response(prompt)

        try:
            start = time.time()
            if getattr(self, "_new_api", False):
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    timeout=timeout,
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
                # openai v0/v3 legacy API
                import openai as _oa
                _oa.api_key = self.api_key
                response = _oa.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    request_timeout=timeout,
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
            print(f"WARNING: OpenAI call failed — {exc}. Using offline fallback.", flush=True)
            result = self._offline_response(prompt)
            result["error"] = str(exc)
            return result

    def generate_with_context(
        self,
        query: str,
        context: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        template: Optional[str] = None,
        timeout: int = 30,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Generate a RAG-style answer given a query and retrieved context.

        If *template* is provided it is used as the prompt body; otherwise a
        default system + user message pair is constructed.
        """
        if self.offline_mode:
            return self._offline_response(query)

        try:
            start = time.time()

            if template:
                filled = template if "{query}" not in template else template.format(
                    query=query, context=context
                )
                messages = [{"role": "user", "content": filled}]
            else:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant. Answer the user's question "
                            "using only the provided context. If the context does not "
                            "contain enough information to answer, say so clearly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
                        ),
                    },
                ]

            if getattr(self, "_new_api", False):
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    timeout=timeout,
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
                    "query": query,
                }
            else:
                import openai as _oa
                _oa.api_key = self.api_key
                response = _oa.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    request_timeout=timeout,
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
                    "query": query,
                }

        except Exception as exc:
            print(f"WARNING: OpenAI call failed — {exc}. Using offline fallback.", flush=True)
            result = self._offline_response(query)
            result["error"] = str(exc)
            result["query"] = query
            return result

    def generate_batch(
        self,
        prompts: List[str],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> List[Dict[str, Any]]:
        results = []
        for prompt in prompts:
            results.append(self.generate(prompt, max_tokens=max_tokens, temperature=temperature))
        return results

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _offline_response(self, prompt: str) -> Dict[str, Any]:
        lower = prompt.lower()
        if "context:" in lower and "question:" in lower:
            ctx_start = lower.find("context:") + len("context:")
            q_start = lower.find("question:")
            context_text = prompt[ctx_start:q_start].strip()
            sentences = [s.strip() for s in context_text.replace("\n", " ").split(".") if s.strip()]
            answer = ". ".join(sentences[:2]) or context_text[:400]
        else:
            answer = prompt[:400]
        return {
            "generated_text": answer,
            "model": self.model,
            "tokens_used": len(answer.split()),
            "offline_mode": True,
        }

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "offline_mode": self.offline_mode,
        }

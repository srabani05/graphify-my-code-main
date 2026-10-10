"""Layer 5 — LLM hook: talk to any OpenAI-compatible chat endpoint by URL.

Provision, not a vendor lock-in: point CODEGRAPH_LLM_URL at OpenAI, Azure
OpenAI, Ollama, vLLM, or any internal gateway exposing /v1/chat/completions.

    export CODEGRAPH_LLM_URL="https://api.openai.com/v1"   # or http://localhost:11434/v1
    export CODEGRAPH_LLM_KEY="sk-..."                      # optional for local servers
    export CODEGRAPH_LLM_MODEL="gpt-4o-mini"               # default: "default"
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

SYSTEM_PROMPT = (
    "You are a senior engineer answering questions about a codebase. "
    "Use ONLY the provided code-graph context: qualified names, call edges, and "
    "source snippets. If the context does not contain the answer, say so "
    "instead of guessing. Cite qualified names like pkg.Class.method in your answer."
)


@dataclass
class LLMConfig:
    base_url: str   # e.g. https://api.openai.com/v1  (no trailing /chat/completions)
    api_key: str | None
    model: str


def config_from_env() -> LLMConfig:
    url = os.environ.get("CODEGRAPH_LLM_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError(
            "CODEGRAPH_LLM_URL is not set. Point it at an OpenAI-compatible "
            "base URL, e.g. export CODEGRAPH_LLM_URL=http://localhost:11434/v1"
        )
    if not url.endswith("/v1"):
        url += "/v1"
    return LLMConfig(
        base_url=url,
        api_key=os.environ.get("CODEGRAPH_LLM_KEY") or None,
        model=os.environ.get("CODEGRAPH_LLM_MODEL", "default"),
    )


def chat(cfg: LLMConfig, messages: list[dict], temperature: float = 0.2,
         timeout: int = 120) -> str:
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    r = requests.post(
        f"{cfg.base_url}/chat/completions",
        headers=headers,
        json={"model": cfg.model, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def ask_with_context(cfg: LLMConfig, question: str, context_md: str) -> str:
    return chat(cfg, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",
         "content": f"CODE GRAPH CONTEXT:\n{context_md}\n\nQUESTION: {question}"},
    ])

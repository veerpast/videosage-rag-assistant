"""Shared LLM provider selection for local and deployed environments."""

import os
import shutil
import subprocess

from langchain_core.runnables import RunnableLambda


def _configured(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")


def run_ollama(prompt_value, model: str | None = None) -> str:
    if not has_ollama():
        raise RuntimeError("Ollama CLI is not available on PATH.")

    if hasattr(prompt_value, "to_string"):
        prompt_text = prompt_value.to_string()
    else:
        prompt_text = str(prompt_value)

    result = subprocess.run(
        ["ollama", "run", model or get_ollama_model(), prompt_text],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_llm(temperature: float = 0.2):
    """Return Groq → Mistral → local Ollama as one fallback-aware Runnable."""
    providers = []

    groq_key = _configured("GROQ_API_KEY")
    if groq_key:
        from langchain_groq import ChatGroq

        providers.append(
            ChatGroq(
                api_key=groq_key,
                model=os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant"),
                temperature=temperature,
                max_retries=2,
            )
        )

    mistral_key = _configured("MISTRAL_API_KEY")
    if mistral_key:
        from langchain_mistralai import ChatMistralAI

        providers.append(
            ChatMistralAI(
                model=os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
                mistral_api_key=mistral_key,
                temperature=temperature,
                max_retries=2,
            )
        )

    if has_ollama():
        providers.append(RunnableLambda(run_ollama))

    if not providers:
        raise RuntimeError(
            "No LLM provider is available. Configure GROQ_API_KEY or "
            "MISTRAL_API_KEY, or install Ollama for local use."
        )

    primary, *fallbacks = providers
    return primary.with_fallbacks(fallbacks) if fallbacks else primary


def provider_summary() -> str:
    configured = []
    if _configured("GROQ_API_KEY"):
        configured.append("Groq")
    if _configured("MISTRAL_API_KEY"):
        configured.append("Mistral")
    if has_ollama():
        configured.append(f"Ollama ({get_ollama_model()})")
    return " → ".join(configured) or "No provider configured"

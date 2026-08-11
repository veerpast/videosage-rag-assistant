"""Shared Groq model configuration."""

import os

from langchain_groq import ChatGroq

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


def get_llm(temperature: float = 0.2) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Add it to .env or deployment secrets."
        )

    return ChatGroq(
        api_key=api_key,
        model=os.getenv("GROQ_LLM_MODEL", DEFAULT_GROQ_MODEL),
        temperature=temperature,
        max_retries=2,
    )


def provider_summary() -> str:
    if not os.getenv("GROQ_API_KEY", "").strip():
        return "Groq (API key not configured)"
    return f"Groq ({os.getenv('GROQ_LLM_MODEL', DEFAULT_GROQ_MODEL)})"

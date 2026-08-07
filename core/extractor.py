#Actionableitems , decision , questions 

import os
import shutil
import subprocess

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")


def run_ollama(prompt_text: str | dict, model: str | None = None) -> str:
    if not has_ollama():
        raise RuntimeError("Ollama CLI is not available on PATH for local fallback.")

    if isinstance(prompt_text, dict):
        prompt_text = prompt_text.get("text", str(prompt_text))
    prompt_text = str(prompt_text)

    model_name = model or get_ollama_model()
    result = subprocess.run(
        ["ollama", "run", model_name, prompt_text],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Ollama fallback failed (return code {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def safe_invoke(chain, prompt_value) -> str:
    try:
        return chain.invoke(prompt_value)
    except Exception as exc:
        print(f"⚠️  LLM call failed: {exc}")
        if not has_ollama():
            raise
        prompt_text = prompt_value.get("text", str(prompt_value)) if isinstance(prompt_value, dict) else str(prompt_value)
        print(f"🔁 Falling back to local Ollama model {get_ollama_model()}")
        return run_ollama(prompt_text)


def get_mistral_api_key() -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please add it to your .env file or export it in your shell."
        )
    return api_key.strip()


def get_llm():
    return ChatMistralAI(
        model = "mistral-small-latest",
        mistral_api_key = get_mistral_api_key(),
        temperature=0.2,
    )



def build_chain(system_prompt : str):
    llm = get_llm()
    return (
        RunnablePassthrough() | RunnableLambda(lambda x : {"text" : x}) |ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human","{text}"),
    ]) | llm |StrOutputParser()
    )

def extract_action_items(transcript:str)->str:
    chain = build_chain(
         "You are an expert meeting analyst. From the meeting transcript, "
        "extract all action items. For each provide:\n"
        "- Task description\n"
        "- Owner (who is responsible)\n"
        "- Deadline (if mentioned, else write 'Not specified')\n\n"
        "Format as a numbered list. If none found say 'No action items found.'"
    )

    return chain.invoke(transcript)


def extract_key_decisions(transcript: str) -> str:
    chain = build_chain(
        "You are an expert meeting analyst. From the meeting transcript, "
        "extract all key decisions made. Format as a numbered list. "
        "If none found say 'No key decisions found.'"
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the meeting transcript, extract all unresolved questions "
        "or topics needing follow-up. Format as a numbered list. "
        "If none found say 'No open questions found.'"
    )
    return chain.invoke(transcript)
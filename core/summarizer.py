import os
import shutil
import subprocess

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter # used to divide the transcript into smaller chunks for summarization
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
        temperature=0.3,
    )


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 3000,
        chunk_overlap = 200
    )

    return splitter.split_text(transcript)

def summarize(transcript : str) -> str:
    llm = get_llm()

    map_prompt = ChatPromptTemplate.from_messages(
        [
        ("system", "Summarize this portion of a meeting transcript concisely."),
        ("human", "{text}"),
    ]
    )

    map_chain = map_prompt | llm | StrOutputParser()

    chunks = split_transcript(transcript)

    chunk_summaries = [safe_invoke(map_chain, {"text": chunk}) for chunk in chunks]

    combined = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages(
        [
        (
            "system",
            "You are an expert meeting summarizer. Combine these partial summaries "
            "into one final professional meeting summary in bullet points.",
        ),
        ("human", "{text}"),
    ]
    )

    combined_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | combined_prompt | llm | StrOutputParser()
    )

    return safe_invoke(combined_chain, combined)

def generate_title(transcipt : str) -> str:
    llm = get_llm()

    

    title_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | 
        ChatPromptTemplate.from_messages([
             (
                "system",
                "Based on the meeting transcript, generate a short professional meeting title "
                "(max 8 words). Only return the title, nothing else.",
            ),
            ("human", "{text}"),
        ])
        | llm
        |StrOutputParser()
    )

    return safe_invoke(title_chain, transcipt[:2000])




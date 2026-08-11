import os

from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
GROQ_TRANSLATION_MODEL = os.getenv("GROQ_TRANSLATION_MODEL", "whisper-large-v3")


def transcribe_chunk_groq(chunk_path: str, translate: bool = False) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=GROQ_API_KEY)
    with open(chunk_path, "rb") as audio_file:
        file_data = (os.path.basename(chunk_path), audio_file.read())

    if translate:
        result = client.audio.translations.create(
            file=file_data,
            model=GROQ_TRANSLATION_MODEL,
            response_format="json",
            temperature=0.0,
        )
    else:
        result = client.audio.transcriptions.create(
            file=file_data,
            model=GROQ_STT_MODEL,
            language="en",
            response_format="json",
            temperature=0.0,
        )
    return result.text.strip()


def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    """Transcribe English or translate Hinglish through Groq Whisper."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is required for audio transcription.")
    return transcribe_chunk_groq(
        chunk_path,
        translate=language.lower() == "hinglish",
    )


def transcribe_all(chunks: list, language: str = "english") -> str:

    full_transcript = ""

    engine = (
        "Groq Whisper translation"
        if language.lower() == "hinglish"
        else "Groq Whisper transcription"
    )
    print(f"Using {engine} for transcription.")

    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        text = transcribe_chunk(chunk, language=language)

        full_transcript += text + " "

    print("Transcription complete.")

    return full_transcript.strip()

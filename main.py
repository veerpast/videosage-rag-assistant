from dotenv import load_dotenv

load_dotenv()  # must run before modules read provider environment variables

from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.summarizer import generate_title, summarize
from core.transcriber import transcribe_all
from utils.audio_processor import process_input


def run_pipeline(
    source: str,
    language: str = "english",
    build_chat: bool = True,
) -> dict:
    print("starting VideoSage")

    res = process_input(source)

    if isinstance(res, str):
        transcript = res
    else:
        transcript = transcribe_all(res, language)

    print(f"raw transcription (first 300 characters ) {transcript[:300]}")

    title = generate_title(transcript)

    summary = summarize(transcript)

    action_item = extract_action_items(transcript)

    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)

    rag_chain = None
    if build_chat:
        try:
            from core.rag_engine import build_rag_chain

            rag_chain = build_rag_chain(transcript)
        except Exception as exc:  # noqa: BLE001 - optional CLI RAG boundary
            print(f"⚠️  Warning: failed to build RAG chain: {exc}")

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


if __name__ == "__main__":
    # CLI entry point
    source = input("Enter YouTube URL or local file path: ").strip()
    language = input("Language (english/hinglish): ").strip() or "english"
    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n📋 Summary:\n{result['summary']}")
    print(f"\n✅ Action Items:\n{result['action_items']}")
    print(f"\n🔑 Key Decisions:\n{result['key_decisions']}")
    print(f"\n❓ Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # Phase 2 — Chat with your meeting via RAG
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")
    if result["rag_chain"] is None:
        print(
            "\n⚠️  RAG chat is unavailable because the retrieval chain failed to initialize."
        )
        print("Please configure GROQ_API_KEY and restart the application.")
        raise SystemExit(0)

    rag_chain = result["rag_chain"]
    from core.rag_engine import ask_question

    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue
        try:
            answer = ask_question(rag_chain, question)
            print(f"\n🤖 Assistant: {answer}\n")
        except Exception as exc:  # noqa: BLE001 - interactive CLI boundary
            print(f"⚠️  Error answering question: {exc}")
            break

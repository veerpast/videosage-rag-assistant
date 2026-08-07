<div align="center">

# VideoSage

### An AI-powered RAG video assistant for clear, searchable knowledge.

A polished AI meeting-intelligence workspace that transcribes video, creates concise summaries, extracts decisions and action items, and lets you chat with the transcript using retrieval-augmented generation.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-Primary%20AI-F55036?style=flat-square)
![Whisper](https://img.shields.io/badge/Whisper-Speech--to--Text-412991?style=flat-square)

</div>

---

## Why this project

Important information is often buried inside hour-long meetings, interviews, lectures, podcasts, and research calls. VideoSage turns that unstructured media into a practical workspace: a transcript, an executive summary, decisions, follow-ups, and a grounded question-answering interface.

The project combines local speech recognition, multilingual transcription, LLM-based information extraction, vector search, and a custom Streamlit interface in one end-to-end pipeline.

## What it does

- Accepts a YouTube URL or a local audio/video file path.
- Downloads or converts media and splits long recordings into manageable chunks.
- Transcribes English audio with Groq Whisper and falls back to local Whisper.
- Supports Hinglish translation through Sarvam AI with Groq fallback.
- Generates a professional title and concise meeting summary.
- Extracts action items, key decisions, and unresolved questions.
- Builds a persistent Chroma vector index from the transcript.
- Answers follow-up questions with retrieval-augmented generation.
- Uses Groq first, Mistral second, and local Ollama as an offline fallback.
- Presents the workflow in a responsive, purpose-designed Streamlit UI.

## Product workflow

```mermaid
flowchart LR
    A[YouTube URL or local media] --> B[Audio preparation]
    B --> C[Whisper or Sarvam transcription]
    C --> D[Mistral analysis]
    D --> E[Summary and structured insights]
    C --> F[Chroma vector store]
    F --> G[RAG conversation]
    E --> H[Streamlit workspace]
    G --> H
```

## Tech stack

| Layer | Technology |
|---|---|
| Interface | Streamlit, custom CSS |
| Media ingestion | yt-dlp, FFmpeg, pydub |
| Speech recognition | Groq Whisper, OpenAI Whisper, Sarvam AI |
| LLM orchestration | LangChain, Groq, Mistral AI |
| Local fallback | Ollama |
| Retrieval | ChromaDB, Hugging Face sentence transformers |
| Language | Python 3.10+ |

## Getting started

### 1. Clone and create an environment

```bash
git clone https://github.com/veerpast/videosage-rag-assistant.git
cd videosage-rag-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

FFmpeg must also be installed on your machine. On macOS:

```bash
brew install ffmpeg
```

### 2. Configure credentials

Copy the environment template and add your keys:

```bash
cp .env.example .env
```

| Variable | Required | Purpose |
|---|---:|---|
| `GROQ_API_KEY` | Recommended | Primary LLM and hosted Whisper transcription |
| `MISTRAL_API_KEY` | No | Secondary cloud LLM fallback |
| `SARVAM_API_KEY` | For Hinglish | Speech-to-text translation |
| `WHISPER_MODEL` | No | Local Whisper model; defaults to `small` |
| `OLLAMA_MODEL` | No | Local fallback model; defaults to `qwen2.5-coder:1.5b` |

### 3. Run the application

```bash
streamlit run app.py
```

Open `http://localhost:8501`, add a source in the sidebar, select the language, and choose **Analyse video**.

## Project structure

```text
videosage-rag-assistant/
├── app.py                    # Streamlit product interface
├── main.py                   # Command-line pipeline entry point
├── core/
│   ├── transcriber.py        # Whisper and Sarvam transcription
│   ├── summarizer.py         # Map-reduce summaries and title generation
│   ├── extractor.py          # Decisions, questions, and action items
│   ├── vector_store.py       # Chroma indexing and retrieval
│   └── rag_engine.py         # Grounded transcript Q&A
├── utils/
│   └── audio_processor.py    # Downloading, conversion, and chunking
├── requirements.txt
├── packages.txt              # Streamlit Community Cloud system package
└── .streamlit/config.toml
```

## Design decisions

- **One provider strategy:** Groq powers both local and deployed runs for consistent behavior.
- **Layered resilience:** Groq → Mistral → Ollama for text generation, with Ollama used only when installed locally.
- **Chunked processing:** long media is split before transcription and summarization.
- **Grounded answers:** questions retrieve relevant transcript segments before generation.
- **Graceful model fallback:** supported LLM calls can use Ollama if the hosted provider fails.
- **Focused interface:** the UI prioritizes source input, processing state, structured results, and conversation without unnecessary dashboard clutter.

## Deployment

The repository is prepared for Streamlit Community Cloud:

1. Push the project to GitHub.
2. In Streamlit Community Cloud, create an app from the repository.
3. Set the entry point to `app.py`.
4. Add `GROQ_API_KEY` and optional fallback keys in **App settings → Secrets**.
5. Deploy.

> Whisper and sentence-transformer models are resource-intensive. For production traffic, moving transcription and vector indexing to background workers or managed services is recommended.

## Roadmap

- Direct drag-and-drop uploads.
- Speaker diarization and timestamped transcript navigation.
- Export to Markdown and PDF.
- Saved workspaces and analysis history.
- Streaming pipeline progress and partial results.

## Author

Built as an end-to-end applied AI project demonstrating media processing, LLM orchestration, retrieval-augmented generation, and product-focused interface design.

---

<div align="center">
If this project is useful, consider giving it a star.
</div>

<div align="center">

# VideoSage

### An AI-powered RAG video assistant for clear, searchable knowledge.

A production-oriented meeting-intelligence platform that can process uploaded media or autonomously attend Google Meet sessions, then generate searchable transcripts, summaries, decisions, and action items.

**Live frontend:** [airag-video-meeting.streamlit.app](https://airag-video-meeting.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-Primary%20AI-F55036?style=flat-square)
![Whisper](https://img.shields.io/badge/Whisper-Speech--to--Text-412991?style=flat-square)

</div>

---

## Why this project

Important information is often buried inside hour-long meetings, interviews, lectures, podcasts, and research calls. VideoSage turns that unstructured media into a practical workspace: a transcript, an executive summary, decisions, follow-ups, and a grounded question-answering interface.

The project combines browser automation, virtual audio capture, multilingual transcription, LLM-based information extraction, private vector search, and a Streamlit frontend across a two-service architecture.

## What it does

- Accepts a YouTube URL or a drag-and-drop audio/video upload.
- Sends an autonomous browser bot to a Google Meet URL through an authenticated webhook.
- Stores private meeting history in Supabase with email/password authentication and PostgreSQL RLS.
- Deletes raw recordings after processing, removes finished meeting URLs, and automatically expires saved results after 1, 7, or 30 days.
- Downloads or converts media and splits long recordings into manageable chunks.
- Transcribes English audio and translates Hinglish with Groq Whisper.
- Generates a professional title and concise meeting summary.
- Extracts action items, key decisions, and unresolved questions.
- Builds an isolated in-memory Chroma index for each active RAG workspace.
- Answers follow-up questions with retrieval-augmented generation.
- Uses Groq for hosted language-model inference.
- Presents the workflow in a responsive, purpose-designed Streamlit UI.

## System architecture

```mermaid
flowchart LR
    U[Authenticated user browser] -->|Supabase email/password auth| S[Streamlit Community Cloud]
    U -->|Public video ID only| C[Caption edge endpoint]
    C -->|Validated public captions| S
    S -->|Bearer token + user JWT| API[Oracle FastAPI worker]
    API --> Q[Persistent sequential job queue]
    Q --> B[Playwright Chromium on Xvfb]
    B --> P[PulseAudio Virtual_Sink]
    P --> F[FFmpeg WAV recording]
    F --> V[VideoSage processing pipeline]
    V --> G[Groq Whisper + Llama 3.1]
    V --> DB[(Supabase PostgreSQL)]
    DB -->|User-scoped history| API
    API --> S
```

The frontend and worker are separate services. Streamlit never receives the
Supabase service-role key and cannot start a browser locally. The Oracle worker
verifies both the private service token and the signed-in user's Supabase JWT.
It runs one browser at a time so simultaneous meetings cannot mix audio on the
shared PulseAudio monitor.

## Media ingestion workflow

```mermaid
flowchart TD
    A[YouTube URL or local media] --> B{Two-Tier Hybrid<br/>Ingestion Router}

    B -->|YouTube URL| C[Fast Path<br/>Fetch captions with youtube-transcript-api]
    C --> D{Transcript available?}
    D -->|Yes| G[Normalized transcript]
    D -->|Cloud IP blocked| C2[Browser caption fetch<br/>public video ID only]
    C2 -->|Caption found| G
    C2 -->|No caption| E

    B -->|Local media| E[Slow Path Fallback<br/>Download or convert media]
    E --> F[FFmpeg and pydub chunking<br/>Groq Whisper transcription]
    F --> G

    G --> H[Groq analysis<br/>Summary and structured insights]
    G --> I[Chroma vector store]
    I --> J[RAG conversation]
    H --> K[Streamlit workspace]
    J --> K
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit Community Cloud, custom CSS |
| Authentication | Supabase Auth, JWT, PostgreSQL RLS |
| Worker API | FastAPI, Uvicorn, authenticated webhooks |
| Browser automation | Playwright Chromium, Xvfb |
| Virtual audio | PulseAudio `Virtual_Sink`, FFmpeg |
| Media ingestion | youtube-transcript-api, browser-side caption fallback, curl-cffi, yt-dlp, FFmpeg, pydub |
| Speech recognition | Groq Whisper transcription and translation |
| LLM orchestration | LangChain, Groq |
| Retrieval | ChromaDB, ONNX `all-MiniLM-L6-v2` embeddings |
| Persistence | Supabase PostgreSQL |
| Infrastructure | Oracle Cloud Always Free (E2 Micro; A1-ready), Caddy, systemd |
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

The application uses Groq for both transcription and Hinglish-to-English
translation, keeping the frontend and worker free of heavyweight local models.

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
| `GROQ_API_KEY` | Yes | Groq LLM inference and hosted Whisper transcription |
| `GROQ_LLM_MODEL` | No | Groq chat model; defaults to `llama-3.1-8b-instant` |
| `GROQ_STT_MODEL` | No | Groq transcription model; defaults to `whisper-large-v3-turbo` |
| `GROQ_TRANSLATION_MODEL` | No | Groq audio translation model; defaults to `whisper-large-v3` |
| `SUPABASE_URL` | Yes | Supabase project URL used by authentication |
| `SUPABASE_ANON_KEY` | Yes | Public Supabase key used for sign-in and sign-up |
| `WORKER_API_URL` | For Meet bot | HTTPS URL of the Oracle worker |
| `WORKER_API_TOKEN` | For Meet bot | Shared Streamlit-to-worker secret |

### 3. Run the application

```bash
streamlit run app.py
```

Open `http://localhost:8501`, add a source in the sidebar, select the language, and choose **Analyse video**.

## Using the live application

Streamlit/GitHub ownership and VideoSage user accounts are separate. Owning the
deployment does not automatically sign you into the product.

1. Open the [live app](https://airag-video-meeting.streamlit.app/).
2. Choose **Create account**, enter an email and a password of at least eight
   characters, accept the privacy notice, and confirm the email if Supabase asks.
3. Return to **Sign in** and use those VideoSage credentials.
4. For an existing video, paste a captioned YouTube URL or upload an audio/video
   file, wait for the caption status when using YouTube, choose the language,
   and select **Analyse video**.
5. Review the generated title, executive summary, action items, decisions, open
   questions, transcript, and grounded RAG chat.
6. For a live Google Meet, paste the Meet URL, choose retention, confirm every
   participant has consented, and select **Send bot to meeting**. Admit
   **VideoSage Assistant** if Meet asks. Results appear in meeting history after
   the meeting ends and processing completes.

Every normal account sees only its own meeting records. Deployment ownership
provides operational access to Streamlit, Oracle, and Supabase, but it is not a
product-level shortcut around account-scoped access controls.

For operator-wide support or incident response, use the Supabase dashboard's
Table Editor or SQL Editor. Do not add an application-level “view everyone's
meetings” bypass: keeping service-role access outside Streamlit preserves RLS
for every public user.

## Project structure

```text
videosage-rag-assistant/
├── app.py                    # Streamlit product interface
├── main.py                   # Command-line pipeline entry point
├── services/
│   ├── auth_client.py        # Supabase email/password authentication
│   └── worker_client.py      # Authenticated Oracle webhook client
├── worker/
│   ├── api.py                # FastAPI queue and worker endpoints
│   ├── meet_bot.py           # Playwright Google Meet attendee
│   ├── audio_capture.py      # PulseAudio and FFmpeg recording
│   └── supabase_store.py     # User-scoped meeting persistence
├── core/
│   ├── transcriber.py        # Groq Whisper transcription and translation
│   ├── summarizer.py         # Map-reduce summaries and title generation
│   ├── extractor.py          # Decisions, questions, and action items
│   ├── vector_store.py       # Chroma indexing and retrieval
│   └── rag_engine.py         # Grounded transcript Q&A
├── utils/
│   └── audio_processor.py    # Downloading, conversion, and chunking
├── supabase/migrations/      # PostgreSQL schema, indexes, and RLS
├── deploy/oracle/            # Xvfb/PulseAudio/Caddy/systemd provisioning
├── docs/ORACLE_DEPLOYMENT.md # Complete free-tier deployment runbook
├── docs/SYSTEM_ARCHITECTURE.md # Detailed trust boundaries and lifecycle
├── docs/DEMO_AND_SOCIAL_GUIDE.md # YouTube, LinkedIn, and X walkthrough scripts
├── docs/USER_AND_OPERATOR_GUIDE.md # Product usage and safe admin operations
├── requirements.txt
├── requirements-worker.txt  # Oracle-only service dependencies
├── packages.txt              # Streamlit Community Cloud system package
└── .streamlit/config.toml
```

## Design decisions

- **One LLM provider:** Groq handles title generation, summarization, structured extraction, and RAG responses in both local and deployed runs.
- **Microservice isolation:** Streamlit handles interaction while Oracle owns long-running browser and audio workloads.
- **Private multi-tenant history:** Supabase Auth identifies users and RLS limits every account to its own meetings.
- **Two-layer worker security:** a service webhook token protects the Oracle API and a user JWT assigns each job to its owner.
- **Persistent bot identity:** Google authentication lives only in a locked-down official-Chrome profile configured through an SSH-only noVNC tunnel; Playwright reuses it only after interactive sign-in.
- **Consent enforcement:** the UI and worker API both require recording-consent confirmation, which is timestamped in PostgreSQL.
- **Data minimization:** raw WAV files and finished Meet URLs are discarded; users can permanently delete results immediately or let the hourly retention worker expire them.
- **Restart-safe queue:** queued and interrupted jobs are recovered from PostgreSQL when the worker restarts.
- **Free-tier egress control:** history queries omit transcripts; full text is fetched only when a user requests it.
- **Database-enforced usage limits:** atomic PostgreSQL functions cap daily analyses and RAG questions so browser refreshes cannot bypass free-tier protection.
- **Hybrid ingestion:** YouTube captions first use direct extraction. When cloud IPs are blocked, a hidden Streamlit component requests public captions from the user's browser and the server validates the video ID, response shape, timestamps, and 5 MB size ceiling. No VideoSage token, Google cookie, or private media is sent. Captionless videos and local media use the audio-processing slow path; if YouTube blocks cloud audio too, the UI asks for a direct upload.
- **Chunked processing:** long media is split before transcription and summarization.
- **Grounded answers:** questions retrieve relevant transcript segments before generation.
- **Lean cloud runtime:** Chroma's CPU ONNX MiniLM path avoids multi-gigabyte PyTorch/CUDA installs on Streamlit Community Cloud.
- **Lean transcription:** the slow path uses hosted Groq Whisper so neither cloud service loads a local speech model.
- **Focused interface:** the UI prioritizes source input, processing state, structured results, and conversation without unnecessary dashboard clutter.

## Deployment

The Streamlit frontend, Supabase backend, and autonomous Oracle worker are
deployed. The worker is available through Caddy-managed HTTPS at
`https://140-245-235-136.sslip.io`; its meeting endpoints require both the
private service token and the signed-in user's Supabase JWT.

1. Deploy the repository's `app.py` on Streamlit Community Cloud.
2. Add `GROQ_API_KEY`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` in **App settings → Secrets**.
3. Apply every SQL file in `supabase/migrations/` to a Supabase Free project in filename order.
4. Deploy the Oracle worker using `docs/ORACLE_DEPLOYMENT.md`.
5. Add `WORKER_API_URL` and `WORKER_API_TOKEN` to Streamlit Secrets.

The complete Oracle VM, Supabase migration, HTTPS, systemd, and Streamlit
configuration procedure is in [the Oracle deployment runbook](docs/ORACLE_DEPLOYMENT.md).
The service-by-service quota and no-overage strategy is documented in the
[zero-cost operating model](docs/ZERO_COST_ARCHITECTURE.md).

This architecture uses [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud), an [Oracle Always Free compute shape](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm), and [Supabase Free](https://supabase.com/pricing). The deployed worker uses E2 Micro because Ampere A1 capacity was unavailable in Hyderabad; it is configured for one meeting at a time with swap-backed memory. Free tiers have resource limits and no production uptime SLA.

## Current deployment status

- Streamlit frontend: deployed.
- Supabase Auth, PostgreSQL schema, RLS, history, and quotas: deployed.
- Privacy notice, user-controlled retention, permanent deletion, and automatic expiry: deployed.
- YouTube and upload analysis: available after sign-in.
- Oracle Google Meet worker: live on an Always Free E2 Micro VM in Hyderabad with Caddy HTTPS, systemd restart recovery, a 4 GB swap safety net, fail2ban, unattended security updates, and authenticated webhook access.

## Roadmap

- Speaker diarization and timestamped transcript navigation.
- Streaming pipeline progress and partial results.
- Speaker-aware transcripts for autonomous meetings.

## Author

Built as an end-to-end applied AI project demonstrating media processing, LLM orchestration, retrieval-augmented generation, and product-focused interface design.

---

<div align="center">
If this project is useful, consider giving it a star.
</div>

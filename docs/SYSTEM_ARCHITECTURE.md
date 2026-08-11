# VideoSage System Design

This is the implementation-level architecture for the public deployment. It
describes what is running now, including free-tier limits and trust boundaries;
it is not a hypothetical scale diagram.

## System context

```mermaid
flowchart LR
    subgraph Client[User trust boundary]
        U[Browser]
        BC[Hidden caption component]
    end

    subgraph Frontend[Streamlit Community Cloud]
        UI[Streamlit UI]
        ROUTER[Two-Tier ingestion router]
        RAG[Chroma RAG workspace]
    end

    subgraph Worker[Oracle Cloud E2 Micro]
        API[FastAPI webhook]
        Q[Sequential asyncio queue]
        BOT[Official Chrome + Playwright]
        AV[Xvfb + PulseAudio Virtual_Sink]
        REC[FFmpeg WAV recorder]
        PIPE[Meeting processing pipeline]
    end

    subgraph Data[Managed free tiers]
        AUTH[Supabase Auth]
        DB[(Supabase PostgreSQL + RLS)]
        GROQ[Groq Whisper + Llama]
    end

    U <-->|Email/password session| AUTH
    U --> UI
    BC -->|Public video ID; no cookies or JWT| CAPTION[Public caption endpoint]
    CAPTION -->|Untrusted text| ROUTER
    UI --> ROUTER
    ROUTER --> GROQ
    ROUTER --> RAG
    UI -->|Service token + user JWT| API
    API -->|Verify JWT| AUTH
    API --> Q --> BOT
    BOT -->|Incoming Meet audio| AV --> REC --> PIPE
    PIPE --> GROQ
    PIPE -->|Owner-scoped results| DB
    UI -->|User JWT| API -->|Owner-filtered history| DB
```

The service-role key exists only on Oracle. Streamlit receives the public
Supabase anon key, while every worker request requires both a private
Streamlit-to-worker token and the current user's JWT.

## Existing-video ingestion

```mermaid
flowchart TD
    A{Input} -->|YouTube URL| ID[Validate host and 11-character video ID]
    A -->|Upload| LIMIT[Validate type and 200 MB limit]

    ID --> DIRECT[youtube-transcript-api]
    DIRECT -->|Captions available| TEXT[Normalized transcript text]
    DIRECT -->|Datacenter IP blocked| BROWSER[Browser-side public-caption request]
    BROWSER --> VALIDATE{ID, header, timestamp<br/>and size validation}
    VALIDATE -->|Valid| TEXT
    VALIDATE -->|Unavailable| AUDIO[yt-dlp audio fallback]
    AUDIO -->|Cloud download blocked| UPLOAD[Ask user for direct upload]

    LIMIT --> WAV[FFmpeg/pydub: mono 16 kHz WAV]
    AUDIO --> WAV
    WAV --> CHUNKS[10-minute chunks]
    CHUNKS --> STT[Groq Whisper]
    STT --> TEXT

    TEXT --> LLM[Groq title, summary and extraction]
    TEXT --> EMBED[ONNX MiniLM embeddings]
    EMBED --> CHROMA[Isolated in-memory Chroma index]
    CHROMA --> QA[Grounded RAG answers]
```

The fast path returns text and deliberately skips Whisper. The slow path returns
audio chunk paths. That explicit type boundary prevents captioned videos from
paying the latency and token cost of speech recognition.

## Autonomous meeting lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued: consent + valid Meet URL
    queued --> joining: worker dequeues job
    joining --> recording: bot joins or is admitted
    joining --> failed: rejected / timeout
    recording --> processing: call ends or room stays empty
    recording --> failed: browser / recorder failure
    processing --> completed: transcript + insights saved
    processing --> failed: transcription / analysis failure
    completed --> deleted: user deletion or retention expiry
    failed --> deleted: user deletion or retention expiry
```

One browser records at a time because all Chrome sessions share one PulseAudio
monitor. Queued or interrupted database jobs are recovered after a worker
restart. The Meet URL is removed when processing finishes; raw audio is deleted
in a `finally` cleanup path.

## Security and data lifecycle

| Boundary | Control |
|---|---|
| Public app → account | Supabase email/password auth and expiring JWTs |
| Streamlit → worker | HTTPS, private bearer token, user JWT |
| User → meeting row | `user_id` ownership checks and PostgreSQL RLS |
| Meet submission | Google Meet host validation plus consent required in UI and API |
| Browser caption payload | Exact video-ID match, expected header/timestamps, 5 MB ceiling |
| Stored results | User-selectable 1/7/30-day expiry and immediate permanent deletion |
| Raw recording | Temporary worker file; deleted after success or failure |
| Secrets | `.env`/Streamlit secrets/systemd environment; excluded from Git |

The operator can access infrastructure and the Supabase service role for
maintenance, so the system does not claim zero-knowledge or end-to-end encrypted
storage. Normal users can see only their own meetings.

## Verified free-tier capacity

| Resource | Enforced operating envelope |
|---|---|
| Oracle worker | E2 Micro, 1 OCPU, 1 GB RAM plus 4 GB swap |
| Concurrent live meetings | 1 recording; additional jobs wait in the sequential queue |
| Maximum meeting duration | 6 hours by default |
| Meetings per account | 3 in a rolling 24-hour window |
| Existing-video analyses | 5 per account per UTC day |
| RAG questions | 20 per account per UTC day |
| Upload size | 200 MB |
| Result retention | 1, 7, or 30 days |

These caps protect a public portfolio deployment from accidental free-tier
overage. They are capacity controls, not claims of enterprise availability.

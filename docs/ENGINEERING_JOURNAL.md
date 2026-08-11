# VideoSage Engineering Journal

This journal records verified engineering problems and decisions from the live
build. It deliberately excludes credentials, account identifiers, private URLs,
and other operational secrets. Metrics should only be reused publicly when they
remain reproducible.

## Hybrid YouTube ingestion under cloud IP blocking

**Problem:** YouTube rejected `yt-dlp` traffic from Streamlit Community Cloud
with HTTP 403 responses. Download attempts also added roughly 45–90 seconds of
latency before analysis could begin.

**Resolution:** The ingestion layer became a two-tier router. The fast path asks
`youtube-transcript-api` for existing captions and passes text directly to the AI
pipeline. Captionless videos and uploaded media use a hardened `yt-dlp` fallback,
`curl-cffi` TLS fingerprinting, audio conversion/chunking, and Groq Whisper.

**Measured result:** On captioned test videos, extraction fell from roughly 45
seconds to roughly 0.5 seconds (about a 98% reduction) while avoiding a video
download entirely.

## Upstream transcript API breaking change

**Problem:** A library upgrade removed the older static
`YouTubeTranscriptApi.get_transcript()` call used by the project.

**Resolution:** The adapter now creates `YouTubeTranscriptApi()` and calls
`fetch(video_id, languages=["en", "hi"])`. Keeping provider-specific behavior in
the ingestion module limited the change's blast radius.

## Type-driven fast/slow pipeline routing

**Problem:** The caption path produces text, while upload and captionless paths
produce audio chunk paths. Sending both through Whisper wasted time, tokens, and
memory.

**Resolution:** `process_input()` returns either `str` or `list[str]`; the CLI and
Streamlit entry points use an explicit type check to bypass speech inference when
text already exists.

## Splitting interactive UI from long-running automation

**Problem:** Streamlit Community Cloud is not suited to a persistent Chromium
session, virtual audio devices, or multi-hour meeting jobs.

**Resolution:** VideoSage moved to two services: Streamlit submits an authenticated
webhook, while an Oracle Always Free VM runs FastAPI, Playwright, Xvfb,
PulseAudio, and FFmpeg. Supabase is the durable job and result boundary.

## Running a browser/audio worker on a 1 GB free VM

**Problem:** The preferred free Ampere shape was unavailable, leaving an E2 Micro
with 1 OCPU and 1 GB RAM. Chromium, FFmpeg, and the analysis client can exceed
that memory during a meeting.

**Resolution:** The deployment uses a 4 GB swap safety net, a sequential queue,
hosted Groq inference, lazy pipeline imports, systemd restart recovery, and daily
per-user quotas. The design intentionally supports one active meeting at a time.

## Google Meet rejecting anonymous automation

**Problem:** The bot reached Meet successfully but Google displayed “You can’t
join this video call” before the organizer could admit it. Changing meeting access
from Trusted to Open did not make an anonymous third-party bot eligible.

**Resolution:** The first attempt still failed because Google rejected
Playwright's bundled Chromium as an insecure automated browser; 2FA did not
change that browser-level decision. The final login helper launches official
Google Chrome directly without Playwright's automation flag, stores the session
in a persistent profile, and lets Playwright reuse it afterward. One-time sign-in
is performed through noVNC bound to localhost and carried over an SSH tunnel;
VNC ports are never public.

## Browser automation surviving changing UI copy

**Problem:** Meet changed its rejection text and used a curly apostrophe plus the
word “video,” so the original end-state detector missed the failure.

**Resolution:** The detector covers the observed copy variants and has a focused
regression test. Failed jobs now terminate cleanly instead of waiting for the full
meeting timeout.

## Supabase optional-row SDK behavior

**Problem:** `supabase-py` returned `None` when `maybe_single()` found no row, but
the persistence adapter assumed a response object with `.data`. A first-time
meeting submission therefore produced an HTTP 500.

**Resolution:** The adapter treats a `None` response as an absent optional value.
A regression test protects idempotent first submissions.

## Privacy on an operator-administered free stack

**Problem:** RLS prevents cross-user access but cannot truthfully make the
infrastructure operator unable to access an operator-managed database. Retaining
raw audio and meeting links would also increase impact unnecessarily.

**Resolution:** The application discloses operator and AI-provider processing,
forces owner-scoped RLS, requires consent for recording and AI processing,
deletes raw WAV files, clears terminal Meet URLs, offers immediate user deletion,
and expires results after a user-selected 1, 7, or 30 days. An hourly worker job
purges expired records.

## Secret and deployment hygiene

**Problem:** A public portfolio repository and multiple hosted services create
several opportunities for accidental credential disclosure or configuration
drift.

**Resolution:** Secrets remain in ignored environment files or platform secret
stores, the public repository is scanned for common credential patterns, the
Oracle API requires both a service token and a valid user JWT, Caddy terminates
HTTPS, and deployments are verified against exact Git commits.

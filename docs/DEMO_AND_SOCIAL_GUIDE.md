# VideoSage Demo and Social Guide

Use a non-confidential test meeting and a captioned public video. Record the
product first, then add narration; this keeps the edit natural and avoids waiting
on AI calls on camera.

## YouTube walkthrough (6–8 minutes)

### 0:00–0:30 — Hook

> An hour-long meeting is easy to record and hard to use. I built VideoSage to
> join a Google Meet, capture only the incoming audio, turn it into structured
> notes, and let each user ask grounded questions afterward. The same pipeline
> also analyses YouTube videos and uploaded media.

Show the deployed URL, sign-in screen, and finished result dashboard.

### 0:30–1:20 — Product flow

Create or sign into a normal VideoSage account. Explain that GitHub/Streamlit
ownership is separate from product authentication. Paste a captioned YouTube
URL, point out **Public captions ready**, run the analysis, expand the transcript,
and ask one answerable RAG question.

### 1:20–2:20 — Autonomous meeting bot

Show the Meet URL, language, retention, and consent controls. Submit a test Meet,
admit **VideoSage Assistant** if required, speak for at least two minutes, leave
the call, and refresh meeting history. Open the completed record and show its
transcript, summary, decisions, action items, and deletion control.

### 2:20–3:40 — Architecture

Use the diagrams in `SYSTEM_ARCHITECTURE.md`.

> Streamlit is only the interactive frontend. It sends an authenticated webhook
> to a FastAPI worker on an Oracle free VM. Official Chrome runs on Xvfb, incoming
> Meet audio is routed through a PulseAudio virtual sink, and FFmpeg records a
> temporary WAV. Groq handles Whisper and Llama inference. Supabase provides auth,
> durable job state, retention, and row-level security.

Explain why the queue is sequential: one shared audio monitor must never mix two
meetings.

### 3:40–5:30 — Engineering problems worth discussing

- YouTube blocked Streamlit/Oracle datacenter IPs with 403/`LOGIN_REQUIRED`.
  Direct captions reduced the normal captioned-video path from about 45 seconds
  to about 0.5 seconds in testing. When the cloud caption request is blocked, a
  browser component retrieves public captions and the Python boundary validates
  the response. Captionless media still uses the audio/Whisper path.
- A `youtube-transcript-api` release replaced the old static method with an
  instantiated client and `fetch`; isolating the adapter kept the change small.
- Google rejected Playwright Chromium as insecure even after 2FA. A one-time,
  SSH-tunnelled noVNC flow signs official Chrome into a dedicated bot profile;
  Playwright then reuses that profile without exposing VNC publicly.
- A 1 GB VM required hosted inference, lazy imports, a 4 GB swap safety net, and
  a single-worker queue.
- Meet UI copy and empty-room behavior changed. Accessible participant counts
  and regression tests replaced brittle text-only automation.
- Streamlit hot reload briefly combined a new `app.py` with a cached old service
  module. Reloading the stateless adapters and adding an API-surface contract
  test prevented the startup regression.

### 5:30–6:40 — Security and production choices

Show RLS, two-token worker auth, consent enforcement, 1/7/30-day retention,
recording deletion, quotas, and the privacy notice. Say clearly that the operator
can access infrastructure for maintenance; do not claim zero knowledge.

### 6:40–end — Close

> This project taught me that production AI engineering is mostly boundary work:
> unreliable providers, browser state, audio routing, job recovery, privacy, and
> cost controls around the model. The repository includes the deployment runbook,
> tests, architecture, and an engineering journal with the decisions behind it.

End on the live app and repository, with both links on screen.

## LinkedIn video (60–75 seconds)

1. **0–7s:** Finished dashboard. “I built a meeting-intelligence system that
   actually joins Google Meet—not just another transcript upload UI.”
2. **7–20s:** Submit a Meet URL, then show the bot. “Streamlit sends an
   authenticated webhook to an Oracle worker running official Chrome, Xvfb,
   PulseAudio, and FFmpeg.”
3. **20–35s:** Show history and RAG. “After the call, Supabase stores private,
   expiring results while Groq generates the transcript, summary, decisions,
   action items, and grounded Q&A.”
4. **35–52s:** Show architecture. “The hard parts were cloud-IP blocks, Google
   rejecting automated browsers, virtual audio on a 1 GB VM, restart-safe jobs,
   and privacy boundaries.”
5. **52–65s:** Show live app. “It runs on free tiers with per-user quotas,
   retention, deletion, and RLS. I documented every trade-off in the repo.”
6. **65–75s:** “I’m looking for an AI engineering internship where this kind of
   end-to-end ownership matters.”

Suggested post:

> I built VideoSage: a deployed AI meeting assistant that joins Google Meet,
> captures incoming audio through a virtual Linux audio stack, and produces
> searchable notes and grounded Q&A. The interesting work was outside the prompt:
> authenticated microservices, browser reliability, cloud-IP blocks, RLS,
> retention, failure recovery, and free-tier cost controls. Live demo + source in
> the comments. I’d value feedback from engineers building production AI systems.

## X video (30–40 seconds)

> Built VideoSage end to end: paste a Meet link, an Oracle worker joins with
> official Chrome, PulseAudio + FFmpeg capture incoming audio, Groq transcribes
> and extracts decisions, and Supabase stores private expiring results. It also
> analyses YouTube/uploads with a two-tier caption/audio router and grounded RAG.
> The public demo is protected by auth, RLS, quotas, and deletion controls.

Suggested post:

> Shipped VideoSage 🎬
>
> • autonomous Google Meet bot  
> • Xvfb + PulseAudio + FFmpeg capture  
> • Groq Whisper/Llama analytics  
> • Supabase Auth, RLS, retention  
> • two-tier YouTube/upload ingestion  
> • grounded RAG over transcripts  
>
> Built on free tiers, with the ugly production failures documented—not hidden.
> Demo + code: [add links]

Keep X and LinkedIn videos captioned, crop tightly around the product, and avoid
showing email addresses, Meet codes, API dashboards, terminal secrets, or the
dedicated bot account.

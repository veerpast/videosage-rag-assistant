# Building VideoSage: The Problems Behind the Demo

VideoSage started as a fairly straightforward RAG project: give it a video,
create a transcript, summarize it, and ask questions about the content.

That version worked locally. Turning it into a public application that could
also join Google Meet was a very different problem.

The difficult work was rarely the final LLM prompt. It was everything around the
model: unreliable third-party services, browser state, Linux audio, background
jobs, authentication, privacy, free-tier resource limits, and deployments that
behaved differently from my laptop.

This document is an honest record of the main problems I faced, the approaches
that did not work, the fixes that reached production, and what I learned from
each one. It intentionally contains no credentials, private meeting links,
account identifiers, or confidential data.

## The final system, in one minute

VideoSage now has three main product flows:

1. A captioned YouTube video follows a text-first fast path and avoids speech
   recognition entirely.
2. Uploaded or captionless media follows an audio path through FFmpeg, chunking,
   and Groq Whisper.
3. A consented Google Meet is handled asynchronously by an Oracle worker running
   an authenticated Chrome profile, Playwright, Xvfb, PulseAudio, and FFmpeg.

Streamlit provides the public interface. Supabase provides authentication,
PostgreSQL persistence, retention, and row-level security. Groq handles hosted
Whisper transcription and Llama-based analysis. Chroma provides the temporary
retrieval layer for grounded questions.

The detailed system design is available in
[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

## Challenge 1: YouTube worked locally and failed in the cloud

### What I saw

My original pipeline downloaded YouTube audio using `yt-dlp`. On my laptop it
worked, but Streamlit Community Cloud frequently returned `HTTP 403 Forbidden`.
Even failed attempts could take 45–90 seconds before the user saw an error.

### What was actually happening

YouTube treated requests from datacenter IP ranges differently from requests
coming from a normal residential connection. This meant that retrying the same
download logic or changing one HTTP header did not address the real problem.

### My first fix: stop downloading when captions already exist

I introduced a two-tier ingestion router:

- **Fast path:** use `youtube-transcript-api` and pass caption text directly into
  the analysis pipeline.
- **Slow path:** when text is unavailable, convert or download media, create
  10-minute audio chunks, and transcribe them with Groq Whisper.

On captioned test videos, this reduced the initial extraction step from roughly
45 seconds to roughly 0.5 seconds—about a 98% reduction in that test—because the
application no longer downloaded a video or ran speech recognition.

### The second failure

YouTube later started blocking caption-only requests from both Streamlit and the
Oracle VM. I tested a modern JavaScript runtime, yt-dlp's EJS challenge solver,
and a Proof-of-Origin token provider. They loaded correctly, but YouTube returned
`LOGIN_REQUIRED` before those tools could solve the request.

I also tested an Oracle caption relay. That failed for the same architectural
reason: it was still a datacenter IP. A free external caption endpoint worked
briefly and then rate-limited the VM as well.

### The production solution

The fallback caption request now runs in a small hidden Streamlit component in
the user's browser. Only the validated 11-character public video ID and language
code are sent. The Python boundary treats the response as untrusted and accepts
it only when:

- the returned video ID matches the requested ID;
- expected transcript metadata and timestamps are present;
- the response remains below a 5 MB ceiling.

No VideoSage JWT, Google cookie, uploaded media, or private meeting content is
included in that request. If captions and the cloud audio fallback are both
unavailable, the application gives a direct-upload instruction rather than
showing raw `yt-dlp` internals.

### What I deliberately rejected

I did not use a personal Google cookie or a residential proxy. Cookies could put
the account at risk and would create a serious privacy and maintenance burden.
A residential proxy would also break the zero-cost operating constraint.

### What I learned

When a feature behaves differently only after deployment, the problem may be the
network identity of the service rather than the code. The strongest optimization
was not making the download faster; it was removing the download from the common
path.

## Challenge 2: A dependency changed underneath the application

### What I saw

After upgrading `youtube-transcript-api`, the older static call
`YouTubeTranscriptApi.get_transcript()` stopped working.

### Root cause and fix

The library had moved to an instantiated client. I isolated the provider-specific
change inside `utils/audio_processor.py`:

```python
yt_api = YouTubeTranscriptApi()
transcript = yt_api.fetch(video_id, languages=["en", "en-US", "en-GB", "hi"])
```

### What I learned

Third-party APIs change. Keeping integration details behind a small adapter makes
the failure local instead of spreading provider-specific syntax throughout the
application.

## Challenge 3: The fast and slow paths returned different kinds of data

### What I saw

The caption path returned text, while the audio path returned a list of chunk
files. Treating both paths identically would send existing text into Whisper,
wasting latency, API usage, and memory.

### The fix

`process_input()` intentionally returns one of two types:

- `str` for transcript text;
- `list[str]` for audio chunk paths.

The CLI and Streamlit entry points perform an explicit type check. Text skips
Whisper and goes directly to analysis; audio chunks are transcribed first.

### What I learned

Dynamic routing needs a clear contract at the boundary. A small, explicit type
decision was easier to reason about than forcing every input through one large
pipeline.

## Challenge 4: Streamlit could not be the meeting worker

### What I initially wanted

The first idea was to launch the Google Meet browser directly from the Streamlit
application.

### Why that design was wrong

A public Streamlit session is not a reliable home for a persistent browser,
virtual display, audio server, or multi-hour recording. The UI can rerun when a
widget changes, sleep when inactive, or restart during deployment.

### The architectural change

I split VideoSage into two services:

- **Streamlit frontend:** authentication, user input, video analysis, meeting
  submission, history, and RAG interaction.
- **Oracle worker:** authenticated FastAPI webhook, sequential job queue,
  Playwright, Chrome, Xvfb, PulseAudio, FFmpeg, processing, and database writes.

Supabase became the durable boundary between an interactive frontend and a
long-running worker.

### What I learned

Microservices are useful when they separate genuinely different lifecycles—not
because the project needs more services. Here, the browser/audio job and the UI
had fundamentally different reliability requirements.

## Challenge 5: The free VM was much smaller than planned

### What I planned

I intended to use Oracle's free Ampere A1 shape with 4 OCPUs and 24 GB RAM.

### What I actually obtained

Ampere capacity was unavailable in the selected region, so the deployed worker
runs on an E2 Micro with 1 OCPU and 1 GB RAM. Chrome, FFmpeg, the API, and the
analysis client can exceed that memory during a real meeting.

### The fix

I adapted the design rather than waiting indefinitely for another shape:

- added a 4 GB swap safety net;
- moved Whisper and Llama inference to Groq;
- used lazy imports for heavy processing modules;
- enforced one active recording at a time;
- added a sequential queue and systemd restart recovery;
- added database-backed per-user usage limits.

### What I learned

Resource constraints can improve architecture. The one-meeting limit is explicit
and safe: two meetings never share the same PulseAudio monitor, and extra jobs
wait rather than corrupting each other's recordings.

## Challenge 6: Google rejected the automated browser identity

### What I saw

The bot reached Google Meet but displayed “You can't join this video call.”
Changing Meet access from Trusted to Open did not solve it. Enabling two-factor
authentication did not solve it either.

### Root cause

This was not a 2FA problem. Google rejected Playwright's bundled Chromium as an
insecure automated browser during sign-in. An anonymous bot also could not join
every meeting reliably.

### The final approach

I created a dedicated Google identity for VideoSage Assistant. A one-time login
helper launches official Google Chrome directly without Playwright's automation
flag and stores the authenticated session in a persistent, locked-down profile.

The interactive login is performed through noVNC bound only to localhost and
reached through an SSH tunnel. VNC ports are never exposed publicly. Playwright
reuses the authenticated profile for future meetings without storing the Google
password in the repository or worker environment.

### What I learned

Security systems reject browser identity, not just credentials. Adding more
authentication factors cannot fix a browser that the provider does not trust.

## Challenge 7: A headless VM has no camera, microphone, or desktop

### What I saw

After sign-in worked, Meet stayed on “Getting ready…” because the VM had no
physical media devices. Another hidden issue was Playwright's default
`--mute-audio` flag, which would also silence the audio stream I needed to record.

### The fix

- Xvfb supplies the virtual display.
- Chrome receives a fake media device and automatic media permission so the
  pre-join checks can finish.
- The bot turns its own microphone and camera off before joining.
- The worker removes Playwright's default audio-mute flag.
- Meet's incoming audio is routed to a PulseAudio `Virtual_Sink` monitor.
- FFmpeg records the monitor as a temporary WAV file.

### What I learned

“Headless browser automation” still depends on operating-system resources. The
browser, display server, audio server, and recorder form one pipeline; debugging
only the DOM misses half the system.

## Challenge 8: Google Meet's interface kept changing

### What I saw

The automation initially depended on visible phrases such as “You're the only
one here.” Meet later changed its wording, punctuation, and end-state behavior.
The participant count correctly changed to `1`, but the text-only detector kept
recording an empty room. In another state, the persistent Chrome profile reopened
directly inside an active call without rendering a Join button.

### The fix

- rejection detection covers the copy variants observed during live testing;
- empty-room detection prefers the accessible People/Participants count and
  keeps text markers only as a compatibility path;
- a visible Leave-call control is treated as proof that the bot is already in
  the meeting;
- a grace period prevents a temporary participant-count change from ending the
  recording immediately;
- focused regression tests cover one-participant, two-participant, rejection,
  and already-inside-call states.

### What I learned

UI copy is not a stable API. Accessible state and multiple independent signals
are usually more reliable than one sentence on the page.

## Challenge 9: A missing Supabase row caused the first meeting to fail

### What I saw

A first-time meeting submission returned HTTP 500 even though “no existing row”
was a valid state.

### Root cause

`supabase-py` returned `None` when `maybe_single()` found no record. My adapter
assumed it would always receive a response object with a `.data` attribute.

### The fix

The persistence layer now treats both `None` and an empty response as “not
found.” A regression test protects first submissions and idempotent retries.

### What I learned

Optional database results need to be modeled as optional values. SDK convenience
methods can still have return-shape edge cases that deserve contract tests.

## Challenge 10: User authentication corrupted a background database write

### What I saw

One live test made it through joining, recording, and Groq transcription, then
failed while saving the final result with:

```text
PGRST303: JWT issued at future
```

### Root cause

The worker used one mutable `supabase-py` client for two different trust levels:

- service-role database writes;
- end-user JWT validation for dashboard requests.

While the meeting was processing, authenticated history polling changed the
shared client's authorization state. The final background write then reached
PostgREST with the wrong JWT.

### The fix

User verification now uses a stateless request to Supabase Auth. The long-lived
database client remains service-role-only. Tests verify that user validation
never calls or mutates the database client's auth session.

### What I learned

Authentication state is shared mutable state. A client that represents an admin
identity should never be reused as an end-user session client, especially inside
concurrent background work.

## Challenge 11: The deployed files were correct, but the app still crashed

### What I saw

After a deployment, Streamlit failed at startup with:

```text
ImportError: cannot import name 'delete_meeting' from 'services.worker_client'
```

The function existed in GitHub and in the deployed file, which made the error
look impossible at first.

### Root cause

Streamlit had hot-reloaded the new `app.py` inside a long-lived Python process
while retaining an older cached `services.worker_client` module. The running
process was combining two revisions.

### The fix

A clean reboot restored a single-revision runtime. The app now reloads its small,
stateless HTTP adapters before importing their public functions. CI also has a
contract test for the complete Streamlit-to-worker API surface.

### What I learned

A deployed filesystem and a running Python interpreter are not always the same
thing. When an import error contradicts the source on disk, module caching and
process lifetime need to be part of the investigation.

## Challenge 12: The Create account button could never become enabled

### What I saw

The signup form required the privacy checkbox, but even after checking it, the
**Create account** button stayed disabled.

### Root cause

The checkbox and button were inside the same `st.form`. Streamlit batches form
widget values and sends them when the form is submitted. The server rendered the
submit button as disabled using the old checkbox value, but a disabled submit
button could never send the new value. I had accidentally created a circular UI
deadlock.

### The fix

The submit button is always clickable. After submission, the server validates:

- an email was provided;
- the privacy notice was accepted;
- the password contains at least eight characters.

The sign-in error is also more useful now: it explains that the account may not
exist and directs first-time users to the **Create account** tab without revealing
whether a specific email is registered. The validation behavior is covered by
unit tests and was verified in the public deployment.

### What I learned

Reactive UI frameworks have event boundaries. A control should not be disabled
using state that can only reach the server through that same control.

## Challenge 13: A useful unit test failed in CI for the wrong reason

### What I saw

The browser-caption validation tests passed locally but failed in the focused CI
environment with `ModuleNotFoundError: streamlit`.

### Root cause

The pure payload validator lived in the same module as the Streamlit custom
component. Importing one small validation function therefore imported the whole
UI framework, even though the test did not need it.

### The fix

I moved the pure validation logic to `services/transcript_validation.py`. The UI
component depends on the validator, but the validator does not depend on
Streamlit. CI can now test the security boundary with a small dependency set.

### What I learned

Dependency direction affects testability. Pure domain and validation code should
sit below framework adapters, not inside them.

## Challenge 14: “Private” needed an honest definition

### The concern

Supabase RLS can prevent one normal user from reading another user's meetings,
but the infrastructure operator still controls Supabase and Oracle. Claiming
zero-knowledge privacy would therefore be misleading.

### The production decision

- normal application queries are owner-scoped and protected by RLS;
- the service-role key exists only on Oracle, never in Streamlit or the browser;
- worker calls require both a private service token and a valid user JWT;
- recording consent is required in both the UI and API;
- raw WAV files are deleted after success or failure;
- finished Meet URLs are cleared;
- users can delete completed or failed results immediately;
- saved results expire after 1, 7, or 30 days;
- the privacy notice clearly discloses operator and AI-provider processing.

There is deliberately no application-level “view every user's meetings” button.
Operator-wide incident response remains in the protected Supabase dashboard.

### What I learned

Security is not only access control; it is also making accurate claims. Data
minimization and honest disclosure matter when perfect technical isolation is
not possible.

## Challenge 15: Keeping a public demo free without pretending it is unlimited

### The constraint

The project needed to stay usable for recruiters without creating surprise
charges or allowing one visitor to consume every free resource.

### The controls

- 5 existing-video analyses per account per UTC day;
- 20 RAG questions per account per UTC day;
- 3 meeting submissions per account in a rolling 24-hour window;
- one active meeting recording across the Oracle worker;
- 200 MB upload limit;
- six-hour meeting ceiling by default;
- bounded queue size and automatic retention cleanup;
- hosted inference instead of loading large models on the VM.

The counters are claimed atomically in PostgreSQL, so refreshing the browser
cannot bypass them.

### What I learned

“Free” still needs capacity engineering. Explicit limits are more professional
than promising unlimited usage on infrastructure that cannot support it.

## What “production-oriented” means for this project

VideoSage is a public portfolio application, not a paid enterprise service with
an uptime SLA. I describe it as production-oriented because it includes the
engineering controls that a real deployed system needs:

- separate frontend and worker lifecycles;
- authenticated service-to-service communication;
- per-user data isolation;
- consent, retention, and deletion;
- restart recovery and idempotency;
- health checks and systemd supervision;
- focused regression tests and CI;
- bounded resource usage;
- secrets outside the repository;
- documented limitations and failure behavior.

That wording is important. The work is real, but the claims should remain honest.

## The biggest lessons I would carry into another AI project

1. **Start with the system boundary, not the prompt.** The model was only one
   component in a much larger reliability problem.
2. **Treat third-party responses and browser state as untrusted.** Validate
   identifiers, sizes, state transitions, and ownership at every boundary.
3. **Separate identities by responsibility.** User JWTs, worker tokens, and
   service-role access should never share mutable client state.
4. **Optimize by removing work.** Caption text made downloading and transcribing
   a video unnecessary on the common path.
5. **Test the failures that actually happened.** Participant counts, missing
   rows, cached modules, auth mutation, and signup state now have focused tests.
6. **Be transparent about limitations.** One meeting at a time and free-tier
   availability are design constraints, not details to hide.

## Short version for an interview or video

> I started with a local RAG video assistant and turned it into a deployed,
> multi-user meeting-intelligence system. The hardest work was outside the LLM:
> YouTube blocked cloud IPs, Google rejected automated browser identity, a 1 GB
> VM needed a virtual display and audio stack, shared authentication state broke
> background writes, Streamlit mixed cached module revisions, and even the signup
> form exposed a reactive-state deadlock. I solved those problems with a two-tier
> ingestion router, an authenticated Oracle worker, official Chrome with a
> persistent profile, PulseAudio and FFmpeg capture, separated auth clients,
> restart-safe jobs, RLS, retention, quotas, and regression tests. The main lesson
> was that production AI engineering is mostly about reliable boundaries around
> the model.

For lower-level incident details, see
[ENGINEERING_JOURNAL.md](ENGINEERING_JOURNAL.md). For the deployed component and
trust-boundary diagrams, see [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

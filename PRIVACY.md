# VideoSage Privacy Notice

Last updated: 11 August 2026

VideoSage is a portfolio demonstration service for non-confidential meetings and
media. Do not use it for medical, legal, financial, employment-confidential, or
otherwise sensitive conversations.

## What is processed

- Account email and authentication metadata are handled by Supabase Auth.
- A submitted Google Meet URL is retained only while the meeting job is active.
- Meeting audio is captured temporarily on the Oracle worker, sent to Groq for
  transcription and analysis, and deleted from the worker after processing.
- The transcript, summary, action items, decisions, and questions are stored in
  Supabase for the retention period selected by the user (1, 7, or 30 days).
- Uploaded media is held in a temporary file during analysis and deleted when
  processing finishes. YouTube captions are processed directly when available.
  If YouTube blocks the hosting provider, the signed-in user's browser sends the
  validated public video ID to youtube-transcript.ai to retrieve public captions;
  no VideoSage account token, Google cookie, uploaded file, or private meeting
  content is included in that request.

## Access and isolation

Supabase Row Level Security limits normal application access to the authenticated
owner of each meeting. Worker requests require both a private service token and a
valid user session. Data is encrypted in transit with HTTPS and uses the hosting
providers' encryption at rest.

The project operator administers Oracle and Supabase and therefore may have
technical access to stored data for security, maintenance, and incident response.
VideoSage does not claim end-to-end encryption or zero-knowledge storage.

## Retention and deletion

Completed and failed meeting records expire automatically after the selected
retention period. The worker checks for expired records at least hourly. Users can
also permanently delete a completed or failed meeting from their dashboard at any
time. The Google Meet URL is removed as soon as processing succeeds or fails.

Raw meeting recordings are not retained. `KEEP_RECORDINGS` is disabled in the
public deployment.

## Third-party processors

- Google Meet supplies the live meeting experience.
- Oracle Cloud runs the meeting worker.
- Groq processes audio and text for transcription and AI analysis.
- Supabase provides authentication and database storage.
- Streamlit Community Cloud hosts the web interface.
- youtube-transcript.ai provides a browser-side fallback for public YouTube
  captions when YouTube blocks cloud-hosted requests.

Each provider processes data under its own terms and privacy policy. Free-tier
services may have operational limits or change their policies.

## User responsibilities

Only submit a meeting after every participant has explicitly agreed to recording
and AI processing. Do not share a Meet link with VideoSage if you are not allowed
to invite a recording bot. Users are responsible for complying with applicable
law and organizational policy.

## Security reports and deletion requests

Use the repository's GitHub Issues page for security reports or account-deletion
requests, but never include passwords, API keys, meeting links, or transcript
content in a public issue.

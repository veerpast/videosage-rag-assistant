# VideoSage User and Operator Guide

## First-time user

1. Open the [public app](https://airag-video-meeting.streamlit.app/).
2. Select **Create account**, enter an email and a password with at least eight
   characters, accept the privacy notice, and submit.
3. If a confirmation email arrives, confirm it and return to **Sign in**.
4. Sign in with the new VideoSage credentials.

A GitHub, Streamlit, Google, or Supabase dashboard login is not automatically a
VideoSage product account. Every person—including the operator—creates or uses a
normal Supabase Auth account in the app.

## Analyse an existing video

### Captioned YouTube video

1. Keep **YouTube URL** selected and paste the full URL.
2. Wait for **Public captions ready — fast path available**.
3. Select English or Hinglish and choose **Analyse video**.
4. Review the title, summary, transcript, action items, decisions, and questions.
5. Ask questions whose answers exist in the transcript.

If public captions are unavailable, use **Retry public captions** once. For a
captionless or cloud-blocked video, download media only when you have permission
and use the upload path instead.

### Uploaded media

1. Select **Upload media**.
2. Choose an MP3, MP4, M4A, WAV, or WebM file up to 200 MB.
3. Select the language and choose **Analyse video**.

The file is temporary and is removed after the request. Uploaded analyses are
session workspaces; autonomous meeting results are the records stored in history.

## Use the autonomous Google Meet bot

1. Create a normal Google Meet and copy its URL.
2. Tell all participants that audio will be recorded and AI-processed.
3. Paste the Meet URL, select language and 1/7/30-day retention, and confirm the
   consent checkbox.
4. Choose **Send bot to meeting**.
5. If Meet asks, admit **VideoSage Assistant**. It joins with its microphone and
   camera off and records incoming meeting audio.
6. Conduct the meeting. For a reliable demo, speak for at least two minutes and
   leave normally rather than ending immediately after admission.
7. Return to VideoSage and choose **Refresh** in meeting history. Processing can
   continue after the call ends; open the record when its status is completed.
8. Use **Delete permanently** when the result is no longer required. Otherwise,
   it expires after the selected retention period.

The free worker handles one live meeting at a time. Additional accepted jobs wait
in a sequential queue so audio from two meetings can never share one recorder.

## Operator access

The operator has two deliberately separate identities:

- **Product identity:** create/sign into a normal VideoSage account in the app.
  It sees only meetings submitted by that account.
- **Infrastructure identity:** GitHub, Streamlit, Oracle, and Supabase dashboard
  access for deployment, support, logs, and incident response.

To inspect all meeting records for legitimate maintenance, open the Supabase
project and use **Table Editor → `meeting_runs`** or a carefully scoped SQL query.
Do not expose the service-role key to Streamlit, add a public admin toggle, or
disable RLS. The current separation protects recruiters and other public users
from another normal account reading their meetings.

## Public demo limits

- 5 existing-video analyses per account per UTC day
- 20 RAG questions per account per UTC day
- 3 meeting submissions per account in a rolling 24-hour window
- 1 active meeting recording at a time across the free Oracle worker
- 200 MB per upload and 6 hours maximum per meeting by default

These limits reset automatically where applicable and prevent free-tier overage.

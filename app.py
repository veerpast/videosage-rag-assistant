import importlib
import tempfile
import time
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import ask_question, build_rag_chain
from core.summarizer import generate_title, summarize
from core.transcriber import transcribe_all
from services import auth_client, worker_client

# Streamlit Community Cloud hot-reloads ``app.py`` without always restarting the
# Python interpreter. Reload our small, stateless HTTP adapters so a deployment
# cannot combine a new app module with stale cached service functions.
importlib.reload(auth_client)
importlib.reload(worker_client)

from services.auth_client import (
    SupabaseAuthError,
    claim_analysis_slot,
    claim_chat_slot,
    refresh_session,
    sign_in,
    sign_out,
    sign_up,
)
from services.auth_client import (
    is_configured as auth_is_configured,
)
from services.worker_client import (
    WorkerClientError,
    delete_meeting,
    get_meeting,
    list_meetings,
    submit_meeting,
)
from services.worker_client import (
    is_configured as worker_is_configured,
)
from utils.audio_processor import process_input

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VideoSage — RAG Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap');

/* ── Root Variables ── */
:root {
    --bg: #f6f7f9;
    --surface: #ffffff;
    --surface-2: #f0f3f7;
    --border: #dfe4eb;
    --accent: #1d4ed8;
    --accent-glow: #2563eb;
    --accent-2: #0f766e;
    --text: #172033;
    --text-muted: #687386;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

/* ── Global Reset ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: var(--bg) !important;
}

/* Animated grid background */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: transparent;
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #fbfcfe !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Newsreader', Georgia, serif !important;
    color: var(--text) !important;
}

/* ── Hero Title ── */
.hero-title {
    font-family: 'Newsreader', Georgia, serif;
    font-size: clamp(2.35rem, 5vw, 4.1rem);
    font-weight: 600;
    line-height: .98;
    margin: 0;
    color: var(--text);
}

.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    color: var(--text-muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.5rem;
}

/* ── Cards ── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(23,32,51,.04);
}

.card:hover {
    border-color: var(--accent);
}

.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
}

.card-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.card-content {
    font-size: 0.92rem;
    line-height: 1.75;
    color: var(--text);
}

/* ── Accent Badge ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.badge-purple { background: #e8efff; color: #1d4ed8; border: 1px solid #c8d8ff; }
.badge-cyan   { background: #e3f5f3; color: #0f766e; border: 1px solid #bde4df; }
.badge-green  { background: #e8f7ef; color: #147a4d; border: 1px solid #c3ead4; }

/* ── Input & Buttons ── */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.2) !important;
}

.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
    text-transform: none !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 7px 18px rgba(29,78,216,.22) !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
}

/* ── Progress / Status ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: var(--surface-2);
    border-radius: 8px;
    margin: 0.4rem 0;
    border: 1px solid var(--border);
    font-size: 0.8rem;
}

.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.dot-active   { background: var(--accent-glow); box-shadow: 0 0 8px var(--accent-glow); animation: pulse 1.5s infinite; }
.dot-done     { background: var(--success); }
.dot-pending  { background: var(--border); }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}

/* ── Chat ── */
.chat-container {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    max-height: 420px;
    overflow-y: auto;
    margin-bottom: 1rem;
}

.chat-msg {
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.chat-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.chat-bubble {
    display: inline-block;
    padding: 0.6rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    line-height: 1.6;
    max-width: 90%;
}

.user-label  { color: var(--accent-glow); }
.bot-label   { color: var(--accent-2); }

.user-bubble { background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.25); align-self: flex-end; }
.bot-bubble  { background: rgba(6,182,212,0.1);  border: 1px solid rgba(6,182,212,0.2);   align-self: flex-start; }

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── Transcript box ── */
.transcript-box {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    font-size: 0.82rem;
    line-height: 1.8;
    max-height: 300px;
    overflow-y: auto;
    color: var(--text-muted);
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Stale Streamlit elements ── */
.stProgress > div > div > div { background: var(--accent) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }
label { color: var(--text-muted) !important; font-size: 0.8rem !important; }

/* scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── Product polish ── */
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stMainBlockContainer"] {
    max-width: 100%;
    width: 100%;
    padding: 3.25rem 3rem 5rem;
}
[data-testid="stSidebarContent"] { padding: 2rem 1.35rem; }
.block-container { position: relative; }

.brand-lockup { display: flex; align-items: center; gap: .75rem; margin-bottom: 2.25rem; }
.brand-mark {
    width: 36px; height: 36px; display: grid; place-items: center;
    color: #fff; background: #172033; border-radius: 10px;
    font-size: .84rem; font-weight: 700; letter-spacing: -.02em;
}
.brand-name { font-size: .94rem; font-weight: 700; letter-spacing: -.02em; color: var(--text); }
.brand-meta { margin-top: .1rem; font-size: .69rem; color: var(--text-muted); }
.sidebar-section { margin: 0 0 .65rem; font-size: .68rem; font-weight: 700; color: var(--text-muted); letter-spacing: .09em; text-transform: uppercase; }
.page-intro { display: grid; grid-template-columns: minmax(0, 1fr) 230px; align-items: end; gap: 2rem; margin-bottom: 2.2rem; }
.page-intro > div:first-child { min-width: 0; }
.page-kicker { color: var(--accent); font-size: .72rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: .7rem; }
.page-description { max-width: 530px; margin: .8rem 0 0; color: var(--text-muted); font-size: .96rem; line-height: 1.65; }
.feature-note { min-width: 0; color: var(--text-muted); font-size: .78rem; line-height: 1.55; padding-bottom: .25rem; }
.empty-shell {
    min-height: 440px; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center;
    gap: 4rem; padding: 3.8rem; background: #fff; border: 1px solid var(--border);
    border-radius: 18px; box-shadow: 0 20px 50px rgba(23,32,51,.055);
}
.empty-title { font-family: 'Newsreader', Georgia, serif; font-size: clamp(2rem,4vw,3.2rem); line-height: 1.04; letter-spacing: -.035em; color: var(--text); }
.empty-copy { margin-top: 1rem; max-width: 480px; color: var(--text-muted); line-height: 1.75; font-size: .94rem; }
.workflow { border-left: 1px solid var(--border); padding-left: 2.25rem; }
.workflow-step { display: flex; gap: 1rem; padding: .85rem 0; }
.workflow-number { width: 27px; height: 27px; flex: 0 0 27px; display: grid; place-items: center; border: 1px solid #cbd5e1; border-radius: 50%; color: var(--accent); font-size: .72rem; font-weight: 700; }
.workflow-label { color: var(--text); font-size: .86rem; font-weight: 600; }
.workflow-detail { color: var(--text-muted); font-size: .74rem; margin-top: .15rem; line-height: 1.45; }
.auth-shell { padding: 1.5rem 0 1rem; }
.auth-kicker { color: var(--accent); font-size: .72rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: .75rem; }
.auth-title { font-family: 'Newsreader', Georgia, serif; font-size: clamp(2.5rem,5vw,4.6rem); font-weight: 600; line-height: .96; letter-spacing: -.035em; color: var(--text); max-width: 650px; }
.auth-copy { max-width: 560px; margin-top: 1.1rem; color: var(--text-muted); font-size: 1rem; line-height: 1.7; }
.auth-points { margin-top: 2rem; display: grid; gap: .8rem; }
.auth-point { display: flex; gap: .75rem; align-items: center; color: var(--text); font-size: .88rem; }
.auth-check { width: 24px; height: 24px; display: grid; place-items: center; border-radius: 50%; background: #e8f7ef; color: #147a4d; font-weight: 700; font-size: .72rem; }

.stButton > button { min-height: 42px; }
.stButton > button:focus:not(:active) { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(37,99,235,.14) !important; }
[data-testid="stExpander"] { background: #fff; border: 1px solid var(--border) !important; border-radius: 14px !important; box-shadow: 0 8px 24px rgba(23,32,51,.04); }
[data-testid="stAlert"] { border-radius: 10px; }

@media (max-width: 850px) {
    [data-testid="stMainBlockContainer"] { padding: 2.5rem 1.15rem 4rem; }
    .page-intro { display: block; }
    .feature-note { margin-top: 1rem; }
    .empty-shell { grid-template-columns: 1fr; gap: 2rem; padding: 2rem 1.4rem; }
    .workflow { border-left: 0; border-top: 1px solid var(--border); padding: 1.25rem 0 0; }
    .hero-title { font-size: 2.7rem; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
    "meeting_job": None,
    "auth_session": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Helpers ────────────────────────────────────────────────────────────────────
def step_status(steps: dict, key: str) -> str:
    s = steps.get(key, "pending")
    if s == "active":
        return "dot-active"
    if s == "done":
        return "dot-done"
    return "dot-pending"


def render_step_bar(label: str, key: str, icon: str):
    css = step_status(st.session_state.pipeline_steps, key)
    st.markdown(
        f"""
    <div class="status-bar">
        <div class="status-dot {css}"></div>
        <span>{icon} {label}</span>
    </div>""",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=15, show_spinner=False)
def load_meeting_history(user_token: str) -> list[dict]:
    return list_meetings(user_token, limit=20)


@st.cache_data(ttl=60, show_spinner=False)
def load_meeting_detail(meeting_id: str, user_token: str) -> dict:
    return get_meeting(meeting_id, user_token)


def display_timestamp(value: str | None) -> str:
    if not value:
        return "Pending"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
            "%d %b %Y, %H:%M UTC"
        )
    except ValueError:
        return value


def safe_html(value: object) -> str:
    return escape(str(value)).replace("\n", "<br>")


def current_user_token() -> str:
    session = st.session_state.auth_session
    if not session:
        raise SupabaseAuthError("Sign in to continue.")
    if session.get("expires_at", 0) <= time.time() + 60:
        session = refresh_session(session["refresh_token"])
        st.session_state.auth_session = session
    return session["access_token"]


def analysis_quota_error(access_token: str) -> str | None:
    try:
        if claim_analysis_slot(access_token):
            return None
        return "Daily free-tier analysis limit reached. Try again tomorrow."
    except SupabaseAuthError as exc:
        return f"Could not verify the analysis quota: {exc}"


# ─── Authentication ─────────────────────────────────────────────────────────────
if not auth_is_configured():
    st.error("Supabase Auth is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY.")
    st.stop()

if not st.session_state.auth_session:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">VS</div><div>'
        '<div class="brand-name">VideoSage</div><div class="brand-meta">'
        "Autonomous meeting intelligence</div></div></div>",
        unsafe_allow_html=True,
    )
    auth_intro, auth_form = st.columns([1.15, 0.85], gap="large")
    with auth_intro:
        st.markdown(
            """
            <div class="auth-shell">
              <div class="auth-kicker">Private AI meeting workspace</div>
              <div class="auth-title">Meetings become<br>useful knowledge.</div>
              <div class="auth-copy">Send VideoSage to a Google Meet or analyse existing media. Get a grounded transcript, concise brief, decisions, action items, and a searchable RAG workspace.</div>
              <div class="auth-points">
                <div class="auth-point"><span class="auth-check">✓</span><span>Private, account-scoped meeting history</span></div>
                <div class="auth-point"><span class="auth-check">✓</span><span>Autonomous Google Meet recording</span></div>
                <div class="auth-point"><span class="auth-check">✓</span><span>Grounded answers from your transcript</span></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with auth_form, st.container(border=True):
        st.markdown("### Welcome to VideoSage")
        st.caption("Sign in to access your account-scoped meeting workspace.")
        st.markdown(
            "[Read the privacy notice](https://github.com/veerpast/"
            "videosage-rag-assistant/blob/main/PRIVACY.md)"
        )
        sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])

        with sign_in_tab:
            with st.form("sign-in-form"):
                login_email = st.text_input("Email", key="login-email")
                login_password = st.text_input(
                    "Password", type="password", key="login-password"
                )
                login_submit = st.form_submit_button(
                    "Sign in", use_container_width=True
                )
            if login_submit:
                try:
                    st.session_state.auth_session = sign_in(login_email, login_password)
                    st.rerun()
                except SupabaseAuthError as exc:
                    st.error(str(exc))

        with sign_up_tab:
            with st.form("sign-up-form"):
                signup_email = st.text_input("Email", key="signup-email")
                signup_password = st.text_input(
                    "Password", type="password", key="signup-password"
                )
                signup_accept = st.checkbox(
                    "I accept the privacy notice and will only process media "
                    "with permission.",
                    key="signup-privacy",
                )
                signup_submit = st.form_submit_button(
                    "Create account",
                    use_container_width=True,
                    disabled=not signup_accept,
                )
            if signup_submit:
                if len(signup_password) < 8:
                    st.error("Use a password with at least 8 characters.")
                else:
                    try:
                        new_session = sign_up(signup_email, signup_password)
                        if new_session:
                            st.session_state.auth_session = new_session
                            st.rerun()
                        st.success(
                            "Account created. Check your email to confirm it, "
                            "then sign in."
                        )
                    except SupabaseAuthError as exc:
                        st.error(str(exc))
    st.stop()

try:
    user_token = current_user_token()
except SupabaseAuthError as exc:
    st.session_state.auth_session = None
    st.error(str(exc))
    st.stop()

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """<div class="brand-lockup"><div class="brand-mark">VS</div><div><div class="brand-name">VideoSage</div><div class="brand-meta">AI-powered RAG video assistant</div></div></div>""",
        unsafe_allow_html=True,
    )
    user = st.session_state.auth_session.get("user", {})
    st.caption(user.get("email", "Signed in"))
    if st.button("Sign out", type="secondary", use_container_width=True):
        try:
            sign_out(user_token)
        except SupabaseAuthError:
            pass
        st.session_state.auth_session = None
        st.session_state.meeting_job = None
        st.rerun()

    st.markdown(
        '<div class="sidebar-section">New analysis</div>', unsafe_allow_html=True
    )
    source_type = st.radio("Source", ["YouTube URL", "Upload media"])
    source = ""
    uploaded_media = None
    if source_type == "YouTube URL":
        source = st.text_input(
            "YouTube URL", placeholder="https://youtube.com/watch?v=..."
        )
    else:
        uploaded_media = st.file_uploader(
            "Audio or video file",
            type=["mp3", "mp4", "m4a", "wav", "webm"],
        )

    language = st.selectbox("Language", ["english", "hinglish"], index=0)

    run_btn = st.button("Analyse video", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown(
        '<div class="sidebar-section">Autonomous meeting bot</div>',
        unsafe_allow_html=True,
    )
    meeting_url = st.text_input(
        "Google Meet URL",
        placeholder="https://meet.google.com/abc-defg-hij",
    )
    meeting_language = st.selectbox(
        "Meeting language",
        ["english", "hinglish"],
        key="meeting_language",
    )
    retention_days = st.selectbox(
        "Keep meeting results for",
        [1, 7, 30],
        index=1,
        format_func=lambda days: f"{days} day" if days == 1 else f"{days} days",
        help="Results are permanently deleted automatically after this period.",
    )
    consent_confirmed = st.checkbox(
        "I confirm all participants consent to recording and AI processing."
    )
    st.caption(
        "Privacy: audio is deleted after processing; results are private to your "
        "account and expire automatically. Use only non-confidential meetings."
    )
    send_bot_btn = st.button(
        "Send bot to meeting",
        use_container_width=True,
        disabled=not worker_is_configured() or not consent_confirmed,
    )
    if not worker_is_configured():
        st.caption("Configure the Oracle worker webhook to enable autonomous meetings.")

    if send_bot_btn:
        if not meeting_url.strip():
            st.error("Enter a Google Meet URL.")
        else:
            try:
                st.session_state.meeting_job = submit_meeting(
                    meeting_url.strip(),
                    user_token,
                    meeting_language,
                    consent_confirmed=True,
                    retention_days=retention_days,
                )
                load_meeting_history.clear()
            except WorkerClientError as exc:
                st.error(str(exc))

    if st.session_state.meeting_job:
        job = st.session_state.meeting_job
        st.success(f"Bot job queued: {job['id'][:8]}")

    if st.session_state.pipeline_done:
        st.markdown("---")
        st.markdown(
            '<div class="sidebar-section">Pipeline status</div>', unsafe_allow_html=True
        )
        for step, icon, label in [
            ("audio", "🔊", "Audio Processing"),
            ("transcript", "📝", "Transcription"),
            ("title", "🏷️", "Title Generation"),
            ("summary", "📋", "Summarisation"),
            ("extract", "🔍", "Extraction"),
            ("rag", "🧠", "RAG Engine"),
        ]:
            render_step_bar(label, step, icon)

# ─── Main Area ──────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="page-intro">
  <div>
    <div class="page-kicker">AI meeting workspace</div>
    <div class="hero-title">Turn every video into<br>clear, useful knowledge.</div>
    <p class="page-description">Transcribe long-form video, surface decisions and action items, then ask grounded questions about the conversation.</p>
  </div>
  <div class="feature-note">Built for interviews, lectures, team meetings, podcasts, and research calls.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Run Pipeline ────────────────────────────────────────────────────────────────
if run_btn:
    if source_type == "YouTube URL" and not source.strip():
        st.error("Please enter a YouTube URL.")
    elif source_type == "Upload media" and uploaded_media is None:
        st.error("Please choose an audio or video file.")
    elif uploaded_media is not None and uploaded_media.size > 200 * 1024 * 1024:
        st.error("Uploads are limited to 200 MB.")
    elif quota_error := analysis_quota_error(user_token):
        st.error(quota_error)
    else:
        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {}

        progress_placeholder = st.empty()

        def update_step(key, state):
            st.session_state.pipeline_steps[key] = state

        uploaded_path = None
        try:
            if uploaded_media is not None:
                suffix = Path(uploaded_media.name).suffix.lower()
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as temp_file:
                    temp_file.write(uploaded_media.getbuffer())
                    uploaded_path = Path(temp_file.name)
                source = str(uploaded_path)

            with progress_placeholder.container():
                st.info("⚙️ Pipeline running — see sidebar for live status…")

            update_step("audio", "active")
            res = process_input(source)
            update_step("audio", "done")

            update_step("transcript", "active")
            if isinstance(res, str):
                transcript = res  # Fast Path: Transcript already retrieved
            else:
                transcript = transcribe_all(
                    res, language
                )  # Slow Path: Process audio chunks through Whisper
            update_step("transcript", "done")

            update_step("title", "active")
            title = generate_title(transcript)
            update_step("title", "done")

            update_step("summary", "active")
            summary = summarize(transcript)
            update_step("summary", "done")

            update_step("extract", "active")
            action_items = extract_action_items(transcript)
            decisions = extract_key_decisions(transcript)
            questions = extract_questions(transcript)
            update_step("extract", "done")

            update_step("rag", "active")
            rag_chain = build_rag_chain(transcript)
            update_step("rag", "done")

            st.session_state.result = {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
            }
            st.session_state.pipeline_done = True
            progress_placeholder.success("✅ Analysis complete!")
            time.sleep(0.5)
            progress_placeholder.empty()
            st.rerun()

        except Exception as e:  # noqa: BLE001 - UI boundary for pipeline providers
            for k in ["audio", "transcript", "title", "summary", "extract", "rag"]:
                if st.session_state.pipeline_steps.get(k) == "active":
                    st.session_state.pipeline_steps[k] = "pending"
            progress_placeholder.error(f"❌ Error: {e}")
        finally:
            if uploaded_path:
                converted = uploaded_path.with_name(
                    f"{uploaded_path.stem}_converted.wav"
                )
                artifacts = [uploaded_path, converted]
                artifacts.extend(converted.parent.glob(f"{converted.name}_chunk_*.wav"))
                for artifact in artifacts:
                    artifact.unlink(missing_ok=True)

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result
    safe_title = safe_html(r["title"])
    safe_summary = safe_html(r["summary"])
    safe_transcript = safe_html(r["transcript"])
    safe_actions = safe_html(r["action_items"])
    safe_decisions = safe_html(r["key_decisions"])
    safe_questions = safe_html(r["open_questions"])

    # Title banner
    st.markdown(
        f"""
    <div class="card">
        <div class="card-title">📌 Session Title</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:700;color:var(--text)">
            {safe_title}
        </div>
    </div>""",
        unsafe_allow_html=True,
    )

    # Top row: summary + transcript
    col1, col2 = st.columns([3, 2], gap="medium")

    with col1:
        st.markdown(
            f"""
        <div class="card">
            <div class="card-title">📋 Summary</div>
            <div class="card-content">{safe_summary}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    with col2, st.expander("📝 Full Transcript", expanded=False):
        st.markdown(
            f'<div class="transcript-box">{safe_transcript}</div>',
            unsafe_allow_html=True,
        )

    # Second row: action items | decisions | questions
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(
            f"""
        <div class="card">
            <div class="card-title">✅ Action Items</div>
            <div class="card-content">{safe_actions}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
        <div class="card">
            <div class="card-title">🔑 Key Decisions</div>
            <div class="card-content">{safe_decisions}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
        <div class="card">
            <div class="card-title">❓ Open Questions</div>
            <div class="card-content">{safe_questions}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    st.markdown(
        "<div style=\"font-family:'Newsreader',Georgia,serif;font-size:1.55rem;font-weight:600;margin-bottom:1rem\">Chat with your meeting</div>",
        unsafe_allow_html=True,
    )

    # Chat history display
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-end">
                    <span class="chat-label user-label">You</span>
                    <div class="chat-bubble user-bubble">{safe_html(msg["content"])}</div>
                </div>"""
            else:
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-start">
                    <span class="chat-label bot-label">🤖 Assistant</span>
                    <div class="chat-bubble bot-bubble">{safe_html(msg["content"])}</div>
                </div>"""
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown(
            """
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">💬</div>
            <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
        </div>""",
            unsafe_allow_html=True,
        )

    # Chat input
    chat_col1, chat_col2 = st.columns([5, 1], gap="small")
    with chat_col1:
        user_input = st.text_input(
            "Your question",
            placeholder="What were the main decisions made?",
            label_visibility="collapsed",
        )
    with chat_col2:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input.strip():
        try:
            chat_allowed = claim_chat_slot(user_token)
        except SupabaseAuthError as exc:
            st.error(f"Could not verify the chat quota: {exc}")
        else:
            if not chat_allowed:
                st.error("Daily free-tier chat limit reached. Try again tomorrow.")
            else:
                with st.spinner("Thinking…"):
                    answer = ask_question(r["rag_chain"], user_input.strip())
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input.strip()}
                )
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": answer}
                )
                st.rerun()

    if st.session_state.chat_history and st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()

else:
    # Empty state
    st.markdown(
        """
    <div class="empty-shell">
      <div>
        <div class="empty-title">Your next conversation,<br>made searchable.</div>
        <div class="empty-copy">
          Add a YouTube link or upload a media file in the sidebar. The assistant turns it into a concise brief you can review, share, and explore through natural-language questions.
        </div>
      </div>
      <div class="workflow">
        <div class="workflow-step"><div class="workflow-number">1</div><div><div class="workflow-label">Add your source</div><div class="workflow-detail">Paste a YouTube URL or upload an audio or video file.</div></div></div>
        <div class="workflow-step"><div class="workflow-number">2</div><div><div class="workflow-label">Let the pipeline work</div><div class="workflow-detail">Audio is prepared, transcribed, summarized, and indexed.</div></div></div>
        <div class="workflow-step"><div class="workflow-number">3</div><div><div class="workflow-label">Review and ask</div><div class="workflow-detail">See decisions and follow-ups, then chat with the transcript.</div></div></div>
      </div>
    </div>""",
        unsafe_allow_html=True,
    )

# ── Autonomous meeting history ─────────────────────────────────────────────────
st.markdown("---")
history_header, history_refresh = st.columns([5, 1])
with history_header:
    st.markdown(
        "<div style=\"font-family:'Newsreader',Georgia,serif;font-size:1.55rem;"
        'font-weight:600">Autonomous meeting history</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Private to your account. Audio is deleted after processing and saved results "
        "expire automatically. The service operator and AI provider process meeting data."
    )
with history_refresh:
    if st.button("Refresh", type="secondary", use_container_width=True):
        load_meeting_history.clear()

if worker_is_configured():
    try:
        meetings = load_meeting_history(user_token)
    except WorkerClientError as exc:
        st.warning(str(exc))
        meetings = []

    if not meetings:
        st.info("No autonomous meeting runs yet.")

    status_icon = {
        "queued": "🕒",
        "running": "🔴",
        "completed": "✅",
        "failed": "⚠️",
    }
    for meeting in meetings:
        title = meeting.get("title") or "Meeting analysis pending"
        status_value = meeting.get("status", "queued")
        created = display_timestamp(meeting.get("created_at"))
        label = f"{status_icon.get(status_value, '•')} {title} · {status_value.title()} · {created}"
        with st.expander(label):
            expiry = display_timestamp(meeting.get("expires_at"))
            if expiry:
                st.caption(f"Scheduled for permanent deletion: {expiry}")
            if status_value == "failed":
                st.error(meeting.get("error_message") or "The meeting worker failed.")
            elif status_value != "completed":
                st.info("The bot is queued or currently attending the meeting.")
            else:
                if st.button(
                    "Open in workspace and chat",
                    key=f"open-meeting-{meeting['id']}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Building a private RAG index…"):
                            detail = load_meeting_detail(meeting["id"], user_token)
                            detail["rag_chain"] = build_rag_chain(detail["transcript"])
                            st.session_state.result = detail
                            st.session_state.chat_history = []
                            st.session_state.pipeline_done = True
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001 - user-facing RAG boundary
                        st.error(f"Could not open this meeting: {exc}")
                st.markdown("#### Summary")
                st.write(meeting.get("summary") or "No summary generated.")
                left, middle, right = st.columns(3)
                with left:
                    st.markdown("##### Action items")
                    st.write(meeting.get("action_items") or "None found.")
                with middle:
                    st.markdown("##### Key decisions")
                    st.write(meeting.get("key_decisions") or "None found.")
                with right:
                    st.markdown("##### Open questions")
                    st.write(meeting.get("open_questions") or "None found.")
                with st.expander("Full transcript"):
                    if st.button("Load transcript", key=f"transcript-{meeting['id']}"):
                        try:
                            detail = load_meeting_detail(meeting["id"], user_token)
                            st.text(
                                detail.get("transcript") or "No transcript available."
                            )
                        except WorkerClientError as exc:
                            st.error(str(exc))
            if status_value in {"completed", "failed"}:
                confirm_delete = st.checkbox(
                    "Confirm permanent deletion",
                    key=f"confirm-delete-{meeting['id']}",
                )
                if st.button(
                    "Delete meeting data",
                    key=f"delete-meeting-{meeting['id']}",
                    type="secondary",
                    disabled=not confirm_delete,
                    use_container_width=True,
                ):
                    try:
                        delete_meeting(meeting["id"], user_token)
                        load_meeting_history.clear()
                        load_meeting_detail.clear()
                        st.success("Meeting data was permanently deleted.")
                        st.rerun()
                    except WorkerClientError as exc:
                        st.error(str(exc))
else:
    st.info(
        "Set WORKER_API_URL and WORKER_API_TOKEN in Streamlit secrets to enable "
        "the Google Meet bot and meeting history."
    )

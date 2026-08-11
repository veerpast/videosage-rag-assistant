# Free-tier Oracle deployment

This deployment keeps the public Streamlit UI separate from the long-running
Google Meet browser. Streamlit sends an authenticated webhook; the Oracle VM
joins and records the meeting; Supabase stores the finished analysis.

## 1. Create the Supabase database

1. Create a Supabase Free project.
2. Open **SQL Editor** and run every file in `supabase/migrations/` in filename
   order. This includes the base schema and privacy-retention controls.
3. In **Authentication → Providers → Email**, enable email/password sign-in.
4. Copy the project URL, anon key, and `service_role` key from
   **Project Settings → API**.

The service-role key belongs only on the Oracle VM. The table has RLS enabled;
authenticated users can select only rows whose `user_id` matches their JWT.
All writes still pass through the authenticated worker API.

The bot also needs a dedicated free Google account. Google Meet's no-cost
meetings require participants and third-party note-taking bots to be signed in;
an anonymous browser can be rejected before the organizer can admit it.

## 2. Prepare the Oracle Always Free VM

Use an Ubuntu `VM.Standard.E2.1.Micro` Always Free instance (1 OCPU, 1 GB RAM)
with a 4 GB swap file and one meeting at a time. The x86-64 shape is required
because Google does not publish its official Linux Chrome build for ARM, and
Google Account sign-in rejects the automated Chromium build. Never select a shape unless Oracle
labels it **Always Free-eligible**. An ephemeral public IPv4 address is free;
replace the Streamlit worker URL if that address changes after recreation.

In the Oracle VCN security list or network security group, allow:

| Port | Source | Purpose |
|---|---|---|
| `22/tcp` | Your public IP only | SSH administration |
| `80/tcp` | `0.0.0.0/0` | Caddy certificate challenge and redirect |
| `443/tcp` | `0.0.0.0/0` | HTTPS worker API |

Do not expose port `8000`; Uvicorn listens only on `127.0.0.1` behind Caddy.

Connect using the downloaded private key:

```bash
chmod 600 /path/to/oracle-key.key
ssh -i /path/to/oracle-key.key ubuntu@<PUBLIC_IP>
```

## 3. Push this repository before provisioning

The setup script deploys the latest `main` branch from GitHub. Commit and push
the worker code first, then run these commands on the VM:

```bash
git clone https://github.com/veerpast/videosage-rag-assistant.git
cd videosage-rag-assistant
```

For free HTTPS without buying a domain, convert the public IP to an sslip.io
hostname. For example, `129.10.20.30` becomes
`129-10-20-30.sslip.io`.

```bash
sudo bash deploy/oracle/setup_oracle.sh <PUBLIC_IP_WITH_DASHES>.sslip.io
```

The script installs Xvfb, PulseAudio, FFmpeg, Caddy, Python dependencies, and
the architecture-compatible Playwright Chromium build. It creates swap on
low-memory instances, enables unattended security updates and fail2ban, creates
a hardened systemd service, and opens only ports 80 and 443 in the VM firewall.

## 4. Configure worker secrets

Generate a webhook token:

```bash
openssl rand -hex 32
```

Edit the root-owned worker environment file:

```bash
sudoedit /etc/videosage/worker.env
```

Fill in `WORKER_API_TOKEN`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, and `GROQ_API_KEY`. Then start the worker:

```bash
sudo systemctl restart videosage-worker
sudo systemctl status videosage-worker --no-pager
curl https://<PUBLIC_IP_WITH_DASHES>.sslip.io/health
```

Expected health response:

```json
{"status":"ok","queued_jobs":0}
```

## 5. Sign in the dedicated Google bot account

The worker uses a persistent browser profile at
`/opt/videosage/browser-profile`. Sign in once through an SSH-only noVNC
tunnel; ports `5901` and `6080` remain bound to localhost and are never opened
in the Oracle firewall. The login helper launches official Google Chrome
directly, without Playwright's automation flag; the worker later reuses the
authenticated profile.

On your computer, keep this tunnel running:

```bash
ssh -L 6080:127.0.0.1:6080 -i /path/to/oracle-key.key ubuntu@<PUBLIC_IP>
```

In the SSH session on the VM:

```bash
sudo systemctl stop videosage-worker
cd /opt/videosage
./deploy/oracle/google_login.sh
```

Open `http://127.0.0.1:6080/vnc.html`, sign in to the dedicated Google account,
and confirm that the Google Account page loads. Press `Ctrl+C` in the VM
terminal, then restart the worker:

```bash
sudo systemctl start videosage-worker
```

Never use the VM's public IP for noVNC and never add Oracle ingress rules for
ports `5901` or `6080`.

## 6. Connect Streamlit Community Cloud

In the existing app at `airag-video-meeting.streamlit.app`, open
**Manage app → Settings → Secrets** and add:

```toml
WORKER_API_URL = "https://<PUBLIC_IP_WITH_DASHES>.sslip.io"
WORKER_API_TOKEN = "the_same_random_token_used_on_oracle"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your_public_anon_key"
```

The anon key is designed for client use; RLS protects the underlying data. Do
not place the service-role key in Streamlit. Groq is the only LLM and speech
provider, and no local speech model is required. Then reboot the Streamlit app.
The **Send bot to meeting** control and autonomous meeting history will become
active automatically.

## 7. Production checks

Check service logs:

```bash
sudo journalctl -u videosage-worker -f
sudo journalctl -u caddy -f
```

Submit a controlled test meeting from Streamlit. The submitter must confirm
participant recording consent. Depending on the meeting access setting, the
organizer may need to admit the signed-in account named **VideoSage Assistant**.
Confirm these states in the dashboard:

```text
queued → running → completed
```

Then verify that the summary, action items, decisions, questions, and on-demand
transcript load from Supabase.

## Operational notes

- The worker intentionally processes one meeting at a time. Multiple Chromium
  sessions cannot share one PulseAudio monitor without mixing their audio.
- Each account is limited to three autonomous meetings per rolling day by
  default. This protects the shared Groq and Oracle free-tier capacity.
- Queued and interrupted jobs are recovered from Supabase after a VM restart.
- Completed WAV files are deleted by default. Set `KEEP_RECORDINGS=true` only
  for debugging because Oracle boot-volume space is finite.
- Completed meeting URLs are removed immediately. Results expire after the
  user-selected 1, 7, or 30 day window; the worker purges expired rows hourly.
- Google Meet requires the persistent bot profile to remain signed in and may
  require organizer admission. Browser selector failures are recorded in the
  meeting's `failed` state.
- Supabase Free can pause after inactivity and has finite database/egress
  quotas. The dashboard fetches transcripts only on demand to reduce egress.
- This is production-minded portfolio infrastructure, but free tiers do not
  provide an uptime SLA.

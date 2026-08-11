# Zero-cost operating model

VideoSage is designed to run without a paid domain, paid compute, or usage
overages. Free-tier exhaustion results in a temporary error or service pause;
the application does not switch to a billable provider.

| Component | Free service | Guardrail |
|---|---|---|
| Public frontend | Streamlit Community Cloud | Heavy browser/audio work stays on Oracle |
| Bot worker | Oracle Ampere A1 Always Free | One Chromium meeting at a time |
| Database and auth | Supabase Free | RLS, on-demand transcript reads, daily per-user quotas |
| LLM and speech API | Groq Free | Free-plan rate limits; no paid fallback |
| HTTPS | Caddy + public CA certificate | Automatic renewal |
| DNS | `<PUBLIC_IP>.sslip.io` | No purchased domain required |

## Current free-tier boundaries

- Oracle documents an Always Free tenancy allowance totaling up to 4 Ampere A1
  OCPUs and 24 GB RAM across Arm instances.
- Supabase Free currently includes a 500 MB database and 5 GB uncached egress;
  inactive projects may pause. Transcript payloads are fetched only on demand.
- Streamlit Community Cloud is free and hibernates inactive apps. A visitor can
  wake the frontend; the Oracle worker remains independent.
- Groq Free applies organization-level request, token, and audio-duration rate
  limits. A `429` is treated as a failed job rather than routed to a paid model.

Official references:

- [Oracle Cloud Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Supabase pricing and Free limits](https://supabase.com/pricing)
- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Groq Free Plan rate limits](https://console.groq.com/docs/rate-limits)

## Avoiding accidental charges

1. Keep the Groq organization on the Free plan. Do not add a paid fallback.
2. Keep the Supabase organization on Free; quota exhaustion restricts service
   instead of creating usage charges.
3. Create only Always Free-eligible Oracle resources and verify the instance is
   labeled **Always Free-eligible** before launching it.
4. Use the provided sslip.io hostname instead of purchasing a domain.
5. Leave `KEEP_RECORDINGS=false` so recordings do not fill the Oracle boot disk.
6. Keep `MAX_MEETINGS_PER_USER_PER_DAY=3` or lower for a public demo.

The database also permits at most five YouTube/upload analyses per user per
calendar day. The slot is claimed atomically through a PostgreSQL function, so
refreshing the browser or opening another session cannot bypass the limit.
RAG chat is separately limited to twenty questions per user per calendar day.

Free tiers do not include a production uptime SLA. This is a robust public
portfolio deployment, not a substitute for paid high-availability infrastructure.

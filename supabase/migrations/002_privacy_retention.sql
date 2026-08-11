-- Privacy-by-design controls for autonomous meeting data.
alter table public.meeting_runs
    alter column meeting_url drop not null;

alter table public.meeting_runs
    add column if not exists retention_days smallint not null default 7,
    add column if not exists expires_at timestamptz;

update public.meeting_runs
set expires_at = created_at + interval '7 days'
where expires_at is null;

-- Existing terminal jobs no longer need their join links either.
update public.meeting_runs
set meeting_url = null
where status in ('completed', 'failed');

alter table public.meeting_runs
    alter column expires_at set default (now() + interval '7 days'),
    alter column expires_at set not null;

alter table public.meeting_runs
    drop constraint if exists meeting_runs_retention_days_check;
alter table public.meeting_runs
    add constraint meeting_runs_retention_days_check
    check (retention_days between 1 and 30);

create index if not exists meeting_runs_expiry_idx
    on public.meeting_runs (expires_at)
    where status in ('completed', 'failed');

-- Reassert least privilege and the cached auth.uid() ownership policy.
alter table public.meeting_runs enable row level security;
alter table public.meeting_runs force row level security;
drop policy if exists meeting_runs_select_own on public.meeting_runs;
create policy meeting_runs_select_own
on public.meeting_runs
for select
to authenticated
using ((select auth.uid()) = user_id);

revoke all on table public.meeting_runs from anon;
grant select on table public.meeting_runs to authenticated;
grant all on table public.meeting_runs to service_role;

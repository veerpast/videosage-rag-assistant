create extension if not exists pgcrypto;

create table if not exists public.meeting_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    meeting_url text not null,
    language text not null default 'english',
    bot_name text not null default 'VideoSage Assistant',
    consent_confirmed_at timestamptz not null,
    status text not null default 'queued',
    title text,
    transcript text,
    summary text,
    action_items text,
    key_decisions text,
    open_questions text,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    started_at timestamptz,
    ended_at timestamptz,
    constraint meeting_runs_language_check
        check (language in ('english', 'hinglish')),
    constraint meeting_runs_status_check
        check (status in ('queued', 'running', 'completed', 'failed')),
    constraint meeting_runs_url_check
        check (meeting_url ~ '^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}/?$'),
    constraint meeting_runs_end_after_start_check
        check (ended_at is null or started_at is null or ended_at >= started_at)
);

create index if not exists meeting_runs_user_created_at_idx
    on public.meeting_runs (user_id, created_at desc);

create index if not exists meeting_runs_active_jobs_idx
    on public.meeting_runs (status, created_at)
    where status in ('queued', 'running');

create unique index if not exists meeting_runs_one_active_user_idx
    on public.meeting_runs (user_id)
    where status in ('queued', 'running');

create or replace function public.set_meeting_runs_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists meeting_runs_set_updated_at on public.meeting_runs;
create trigger meeting_runs_set_updated_at
before update on public.meeting_runs
for each row execute function public.set_meeting_runs_updated_at();

alter table public.meeting_runs enable row level security;

-- Only the Oracle worker uses the service-role key. No anon/authenticated
-- write policy is created. Authenticated users can read only their own rows.
drop policy if exists meeting_runs_select_own on public.meeting_runs;
create policy meeting_runs_select_own
on public.meeting_runs
for select
to authenticated
using ((select auth.uid()) = user_id);

revoke all on table public.meeting_runs from anon;
grant select on table public.meeting_runs to authenticated;
grant all on table public.meeting_runs to service_role;

create table if not exists public.daily_usage (
    user_id uuid not null references auth.users(id) on delete cascade,
    usage_date date not null default current_date,
    analysis_count smallint not null default 0,
    chat_count smallint not null default 0,
    primary key (user_id, usage_date),
    constraint daily_usage_analysis_count_check check (analysis_count between 0 and 5),
    constraint daily_usage_chat_count_check check (chat_count between 0 and 20)
);

alter table public.daily_usage enable row level security;

drop policy if exists daily_usage_select_own on public.daily_usage;
create policy daily_usage_select_own
on public.daily_usage
for select
to authenticated
using ((select auth.uid()) = user_id);

revoke all on table public.daily_usage from anon;
grant select on table public.daily_usage to authenticated;
grant all on table public.daily_usage to service_role;

create or replace function public.claim_analysis_slot()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    claimed_count smallint;
begin
    if auth.uid() is null then
        return false;
    end if;

    insert into public.daily_usage (user_id, usage_date, analysis_count)
    values (auth.uid(), current_date, 1)
    on conflict (user_id, usage_date)
    do update
        set analysis_count = public.daily_usage.analysis_count + 1
        where public.daily_usage.analysis_count < 5
    returning analysis_count into claimed_count;

    return claimed_count is not null;
end;
$$;

revoke all on function public.claim_analysis_slot() from public, anon;
grant execute on function public.claim_analysis_slot() to authenticated;

create or replace function public.claim_chat_slot()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    claimed_count smallint;
begin
    if auth.uid() is null then
        return false;
    end if;

    insert into public.daily_usage (user_id, usage_date, chat_count)
    values (auth.uid(), current_date, 1)
    on conflict (user_id, usage_date)
    do update
        set chat_count = public.daily_usage.chat_count + 1
        where public.daily_usage.chat_count < 20
    returning chat_count into claimed_count;

    return claimed_count is not null;
end;
$$;

revoke all on function public.claim_chat_slot() from public, anon;
grant execute on function public.claim_chat_slot() to authenticated;

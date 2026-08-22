-- =====================================================================
-- ProstudioX — Supabase schema
-- Run in the Supabase SQL Editor (as the project owner).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Videos table (content library + job tracking)
-- ---------------------------------------------------------------------
create table if not exists public.videos (
    id               uuid primary key default gen_random_uuid(),
    topic            text not null,
    script           text,
    title            text,
    description      text,
    hashtags         text,
    storage_path     text,                 -- path inside the 'videos' bucket
    public_url       text,                 -- full URL (filled by the client)
    duration_seconds int,
    status           text not null default 'queued',
        -- queued | generating | done | failed | published
    error            text,
    created_at       timestamptz not null default now(),
    published_at     timestamptz
);

create index if not exists idx_videos_status on public.videos (status);

-- Row Level Security: nothing is readable via the anon/public key.
-- The pipeline writes with the service_role key (bypasses RLS), so this
-- table stays private even though the project is public.
alter table public.videos enable row level security;

-- (No permissive policies are added on purpose — service_role only.)

-- ---------------------------------------------------------------------
-- 2) Storage bucket for finished videos
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('videos', 'videos', true)
on conflict (id) do nothing;

-- Public reads of the bucket are fine (videos are meant to be watched),
-- but writes still require the service_role key.
create policy "public read videos" on storage.objects
  for select using (bucket_id = 'videos');

-- ---------------------------------------------------------------------
-- 3) Vault secrets + a service_role-only reader
-- ---------------------------------------------------------------------
-- Store each API key once (run in SQL editor as owner):
--
--   insert into vault.secrets (name, secret) values ('OPENAI_API_KEY', 'sk-...');
--   insert into vault.secrets (name, secret) values ('PEXELS_API_KEY', '...');
--   insert into vault.secrets (name, secret) values ('PIXABAY_API_KEY', '...');
--   insert into vault.secrets (name, secret) values ('GEMINI_API_KEY', '...');
--
-- The RPC below returns a decrypted secret ONLY to callers authenticated
-- with the service_role key (or the owner). The anon key cannot read it.

create or replace function public.get_secret(secret_name text)
returns table (secret_value text)
language sql
security definer
set search_path = public
as $$
  select decrypted_secret
  from vault.decrypted_secrets
  where name = secret_name
$$;

revoke all on function public.get_secret(text) from public, anon, authenticated;
grant execute on function public.get_secret(text) to service_role;

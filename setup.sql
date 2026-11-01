-- HushKey: run this once in Supabase -> SQL Editor -> New query -> Run.
--
-- Creates the table that holds each vault's recovery secret, and the rules
-- (Row Level Security) that make sure a person can only ever read or write
-- THEIR OWN row, and only after signing in with an email code.

create table if not exists public.recovery_keys (
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  vault_id   text not null check (char_length(vault_id) between 8 and 64),
  secret     text not null check (char_length(secret) between 40 and 100),
  created_at timestamptz not null default now(),
  primary key (user_id, vault_id)
);

alter table public.recovery_keys enable row level security;

drop policy if exists "read own recovery key"   on public.recovery_keys;
drop policy if exists "add own recovery key"    on public.recovery_keys;
drop policy if exists "update own recovery key" on public.recovery_keys;

create policy "read own recovery key" on public.recovery_keys
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "add own recovery key" on public.recovery_keys
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "update own recovery key" on public.recovery_keys
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- Signed-out visitors get nothing; signed-in users can only touch their rows (above).
revoke all on public.recovery_keys from anon;
grant select, insert, update on public.recovery_keys to authenticated;

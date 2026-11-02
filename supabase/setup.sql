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


-- ---------------------------------------------------------------------------
-- v2.0.9: SYNC. One encrypted vault per account.
-- `data` is the vault exactly as HushKey encrypts it. The server can't read
-- any login (the key is the user's master password, which never leaves their
-- computer), and HushKey checks a tamper seal on everything it downloads.
-- Safe to run this whole file again: nothing existing is deleted.
-- ---------------------------------------------------------------------------

create table if not exists public.vaults (
  user_id    uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  vault_id   text not null check (char_length(vault_id) between 8 and 64),
  data       text not null check (char_length(data) < 20000000),
  rev        bigint not null default 1,
  updated_at timestamptz not null default now()
);

alter table public.vaults enable row level security;

drop policy if exists "read own vault"   on public.vaults;
drop policy if exists "add own vault"    on public.vaults;
drop policy if exists "update own vault" on public.vaults;

create policy "read own vault" on public.vaults
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "add own vault" on public.vaults
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "update own vault" on public.vaults
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.vaults from anon;
grant select, insert, update on public.vaults to authenticated;

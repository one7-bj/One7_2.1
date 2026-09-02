-- ============================================================
-- ONE7 2.1.1 - SCHEMA MULTI-CABINET
-- Exécuter dans Supabase SQL Editor.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists public.cabinets (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    legal_name text,
    ifu text,
    rccm text,
    address text,
    phone text,
    email text,
    currency text not null default 'XOF',
    logo_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.cabinet_members (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null default 'assistant' check (role in ('admin','manager','accountant','assistant','viewer')),
    created_at timestamptz not null default now(),
    unique(cabinet_id, user_id)
);

create index if not exists idx_cabinet_members_user on public.cabinet_members(user_id);
create index if not exists idx_cabinet_members_cabinet on public.cabinet_members(cabinet_id);

create or replace function public.is_cabinet_member(target_cabinet uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
    select exists (
        select 1 from public.cabinet_members
        where cabinet_id = target_cabinet and user_id = auth.uid()
    );
$$;

create or replace function public.has_cabinet_role(target_cabinet uuid, allowed_roles text[])
returns boolean
language sql
security definer
stable
set search_path = public
as $$
    select exists (
        select 1 from public.cabinet_members
        where cabinet_id = target_cabinet
          and user_id = auth.uid()
          and role = any(allowed_roles)
    );
$$;

create table if not exists public.clients (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    name text not null,
    ifu text,
    rccm text,
    legal_form text,
    tax_regime text,
    activity text,
    address text,
    phone text,
    email text,
    contact_name text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_clients_cabinet on public.clients(cabinet_id);
create index if not exists idx_clients_ifu on public.clients(ifu);

create table if not exists public.exercises (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    client_id uuid not null references public.clients(id) on delete cascade,
    fiscal_year integer not null,
    start_date date not null,
    end_date date not null,
    status text not null default 'open' check (status in ('open','closed','locked')),
    created_at timestamptz not null default now(),
    unique(client_id, fiscal_year)
);
create index if not exists idx_exercises_cabinet_client on public.exercises(cabinet_id, client_id);

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    client_id uuid references public.clients(id) on delete set null,
    exercise_id uuid references public.exercises(id) on delete set null,
    file_name text not null,
    storage_path text,
    document_type text not null default 'invoice',
    document_date date,
    supplier_name text,
    supplier_ifu text,
    invoice_number text,
    currency text not null default 'XOF',
    amount_ht numeric(18,2) not null default 0,
    amount_tax numeric(18,2) not null default 0,
    amount_ttc numeric(18,2) not null default 0,
    tax_rate numeric(8,4),
    ai_confidence numeric(6,3),
    extraction_json jsonb,
    status text not null default 'pending' check (status in ('pending','processed','validated','anomaly','rejected')),
    anomaly_message text,
    validated_by uuid references auth.users(id) on delete set null,
    validated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_documents_cabinet on public.documents(cabinet_id);
create index if not exists idx_documents_client on public.documents(client_id);
create index if not exists idx_documents_status on public.documents(status);

create table if not exists public.journal_entries (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    client_id uuid references public.clients(id) on delete set null,
    exercise_id uuid references public.exercises(id) on delete set null,
    document_id uuid references public.documents(id) on delete set null,
    journal_code text not null default 'OD',
    entry_number text,
    entry_date date not null,
    label text,
    source text default 'manual' check (source in ('manual','import','ai','bank')),
    status text not null default 'draft' check (status in ('draft','validated','posted','locked')),
    created_by uuid references auth.users(id) on delete set null,
    validated_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_entries_cabinet on public.journal_entries(cabinet_id);
create index if not exists idx_entries_client on public.journal_entries(client_id);

create table if not exists public.journal_lines (
    id uuid primary key default gen_random_uuid(),
    journal_entry_id uuid not null references public.journal_entries(id) on delete cascade,
    account_number text not null,
    account_label text,
    label text,
    debit numeric(18,2) not null default 0 check (debit >= 0),
    credit numeric(18,2) not null default 0 check (credit >= 0),
    created_at timestamptz not null default now(),
    check (not (debit > 0 and credit > 0))
);
create index if not exists idx_journal_lines_entry on public.journal_lines(journal_entry_id);

create table if not exists public.tax_declarations (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    client_id uuid not null references public.clients(id) on delete cascade,
    exercise_id uuid references public.exercises(id) on delete set null,
    tax_type text not null default 'TVA',
    period_start date not null,
    period_end date not null,
    amount_collected numeric(18,2) not null default 0,
    amount_deductible numeric(18,2) not null default 0,
    amount_net numeric(18,2) not null default 0,
    aib_amount numeric(18,2) not null default 0,
    status text not null default 'draft' check (status in ('draft','review','ready','submitted','paid','anomaly')),
    due_date date,
    submitted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_tax_decl_cabinet_client on public.tax_declarations(cabinet_id, client_id);

create table if not exists public.audit_logs (
    id uuid primary key default gen_random_uuid(),
    cabinet_id uuid not null references public.cabinets(id) on delete cascade,
    user_id uuid references auth.users(id) on delete set null,
    action text not null,
    entity_type text,
    entity_id uuid,
    metadata jsonb,
    created_at timestamptz not null default now()
);
create index if not exists idx_audit_cabinet on public.audit_logs(cabinet_id, created_at desc);

-- Fonction de création atomique d'un cabinet + membre admin.
create or replace function public.create_cabinet(
    cabinet_name text,
    cabinet_legal_name text default null,
    cabinet_ifu text default null,
    cabinet_rccm text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    new_cabinet uuid;
begin
    if auth.uid() is null then
        raise exception 'Utilisateur non authentifié';
    end if;

    insert into public.cabinets(name, legal_name, ifu, rccm)
    values (trim(cabinet_name), nullif(trim(cabinet_legal_name), ''), nullif(trim(cabinet_ifu), ''), nullif(trim(cabinet_rccm), ''))
    returning id into new_cabinet;

    insert into public.cabinet_members(cabinet_id, user_id, role)
    values (new_cabinet, auth.uid(), 'admin');

    return new_cabinet;
end;
$$;

-- RLS
alter table public.cabinets enable row level security;
alter table public.cabinet_members enable row level security;
alter table public.clients enable row level security;
alter table public.exercises enable row level security;
alter table public.documents enable row level security;
alter table public.journal_entries enable row level security;
alter table public.journal_lines enable row level security;
alter table public.tax_declarations enable row level security;
alter table public.audit_logs enable row level security;

-- Cabinets
 drop policy if exists cabinets_select_member on public.cabinets;
create policy cabinets_select_member on public.cabinets for select using (public.is_cabinet_member(id));
drop policy if exists cabinets_update_admin on public.cabinets;
create policy cabinets_update_admin on public.cabinets for update using (public.has_cabinet_role(id, array['admin','manager'])) with check (public.has_cabinet_role(id, array['admin','manager']));

-- Members
 drop policy if exists members_select on public.cabinet_members;
create policy members_select on public.cabinet_members for select using (user_id = auth.uid() or public.has_cabinet_role(cabinet_id, array['admin','manager']));
drop policy if exists members_insert_admin on public.cabinet_members;
create policy members_insert_admin on public.cabinet_members for insert with check (public.has_cabinet_role(cabinet_id, array['admin','manager']));
drop policy if exists members_update_admin on public.cabinet_members;
create policy members_update_admin on public.cabinet_members for update using (public.has_cabinet_role(cabinet_id, array['admin','manager'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager']));
drop policy if exists members_delete_admin on public.cabinet_members;
create policy members_delete_admin on public.cabinet_members for delete using (public.has_cabinet_role(cabinet_id, array['admin','manager']));

-- Tables cabinet-scoped
create policy clients_select_member on public.clients for select using (public.is_cabinet_member(cabinet_id));
create policy clients_write on public.clients for all using (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant']));

create policy exercises_select_member on public.exercises for select using (public.is_cabinet_member(cabinet_id));
create policy exercises_write on public.exercises for all using (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant']));

create policy documents_select_member on public.documents for select using (public.is_cabinet_member(cabinet_id));
create policy documents_write on public.documents for all using (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant']));

create policy entries_select_member on public.journal_entries for select using (public.is_cabinet_member(cabinet_id));
create policy entries_write on public.journal_entries for all using (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant']));

create policy lines_select_member on public.journal_lines for select using (exists (select 1 from public.journal_entries e where e.id = journal_entry_id and public.is_cabinet_member(e.cabinet_id)));
create policy lines_write on public.journal_lines for all using (exists (select 1 from public.journal_entries e where e.id = journal_entry_id and public.has_cabinet_role(e.cabinet_id, array['admin','manager','accountant','assistant']))) with check (exists (select 1 from public.journal_entries e where e.id = journal_entry_id and public.has_cabinet_role(e.cabinet_id, array['admin','manager','accountant','assistant'])));

create policy tax_select_member on public.tax_declarations for select using (public.is_cabinet_member(cabinet_id));
create policy tax_write on public.tax_declarations for all using (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant'])) with check (public.has_cabinet_role(cabinet_id, array['admin','manager','accountant','assistant']));

create policy audit_select_member on public.audit_logs for select using (public.has_cabinet_role(cabinet_id, array['admin','manager']));
create policy audit_insert_member on public.audit_logs for insert with check (public.is_cabinet_member(cabinet_id));

grant execute on function public.create_cabinet(text,text,text,text) to authenticated;
grant execute on function public.is_cabinet_member(uuid) to authenticated;
grant execute on function public.has_cabinet_role(uuid,text[]) to authenticated;

-- Vue pratique pour le dashboard (facultative).
create or replace view public.cabinet_dashboard_counts as
select
    c.id as cabinet_id,
    (select count(*) from public.clients x where x.cabinet_id = c.id) as clients_count,
    (select count(*) from public.documents x where x.cabinet_id = c.id) as documents_count,
    (select count(*) from public.journal_entries x where x.cabinet_id = c.id) as entries_count,
    (select count(*) from public.documents x where x.cabinet_id = c.id and x.status = 'anomaly') as anomalies_count
from public.cabinets c;

-- ============================================================
-- ONE7 V2.2 — STORAGE DES DOCUMENTS
-- ============================================================
-- À exécuter APRÈS le schéma One7 V2.2 consolidé.
-- Le bucket est privé : les fichiers ne sont pas publics.

insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do update set public = false;

-- Lecture : uniquement les membres du cabinet correspondant au premier dossier du chemin.
drop policy if exists "one7_documents_storage_select" on storage.objects;
create policy "one7_documents_storage_select"
on storage.objects
for select
to authenticated
using (
    bucket_id = 'documents'
    and public.is_cabinet_member((storage.foldername(name))[1]::uuid)
);

-- Écriture : seuls les rôles opérationnels peuvent déposer des fichiers.
drop policy if exists "one7_documents_storage_insert" on storage.objects;
create policy "one7_documents_storage_insert"
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'documents'
    and public.can_write_cabinet((storage.foldername(name))[1]::uuid)
);

-- Mise à jour : rôles opérationnels uniquement.
drop policy if exists "one7_documents_storage_update" on storage.objects;
create policy "one7_documents_storage_update"
on storage.objects
for update
to authenticated
using (
    bucket_id = 'documents'
    and public.can_write_cabinet((storage.foldername(name))[1]::uuid)
)
with check (
    bucket_id = 'documents'
    and public.can_write_cabinet((storage.foldername(name))[1]::uuid)
);

-- Suppression physique : réservée aux administrateurs/expert-comptables.
drop policy if exists "one7_documents_storage_delete" on storage.objects;
create policy "one7_documents_storage_delete"
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'documents'
    and public.is_cabinet_admin((storage.foldername(name))[1]::uuid)
);

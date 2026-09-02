-- ONE7 V2.2 — SCHEMA CONSOLIDE
-- V2 + V2.1 + durcissement multi-cabinet
-- ATTENTION : ce script reconstruit la base et supprime les anciennes tables One7.

BEGIN;

-- ============================================================
-- ONE7 V2
-- SCHEMA COMPLET
-- VERSION : 2.0
-- ============================================================

BEGIN;

-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- 1. SUPPRESSION DE L'ANCIENNE ARCHITECTURE
-- ============================================================

DROP VIEW IF EXISTS public.client_dashboard CASCADE;

DROP TABLE IF EXISTS public.audit_logs CASCADE;
DROP TABLE IF EXISTS public.accounting_controls CASCADE;
DROP TABLE IF EXISTS public.tax_declarations CASCADE;
DROP TABLE IF EXISTS public.accounting_entry_lines CASCADE;
DROP TABLE IF EXISTS public.accounting_entries CASCADE;
DROP TABLE IF EXISTS public.journals CASCADE;
DROP TABLE IF EXISTS public.chart_of_accounts CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.exercises CASCADE;
DROP TABLE IF EXISTS public.clients CASCADE;
DROP TABLE IF EXISTS public.cabinet_members CASCADE;
DROP TABLE IF EXISTS public.cabinets CASCADE;

-- Anciennes tables One7
DROP TABLE IF EXISTS public.imputations CASCADE;
DROP TABLE IF EXISTS public.plan_comptable CASCADE;
DROP TABLE IF EXISTS public.cci CASCADE;
DROP TABLE IF EXISTS public.parametres_generaux CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;


-- ============================================================
-- 2. FONCTION GENERALE updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- ============================================================
-- 3. CABINETS
-- ============================================================

CREATE TABLE public.cabinets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    legal_name TEXT,

    ifu TEXT,
    rccm TEXT,

    address TEXT,
    phone TEXT,
    email TEXT,

    currency TEXT NOT NULL DEFAULT 'XOF',

    logo_url TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX idx_cabinets_name
ON public.cabinets(name);


CREATE TRIGGER cabinets_updated_at
BEFORE UPDATE ON public.cabinets
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 4. MEMBRES DU CABINET
-- ============================================================

CREATE TABLE public.cabinet_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    user_id UUID NOT NULL
        REFERENCES auth.users(id)
        ON DELETE CASCADE,

    role TEXT NOT NULL DEFAULT 'comptable',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT cabinet_members_role_check
    CHECK (
        role IN (
            'admin',
            'expert_comptable',
            'comptable',
            'assistant',
            'lecture'
        )
    ),

    CONSTRAINT cabinet_members_unique
    UNIQUE(cabinet_id, user_id)
);


CREATE INDEX idx_cabinet_members_user
ON public.cabinet_members(user_id);

CREATE INDEX idx_cabinet_members_cabinet
ON public.cabinet_members(cabinet_id);


-- ============================================================
-- 5. CLIENTS
-- ============================================================

CREATE TABLE public.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,
    legal_name TEXT,

    ifu TEXT,
    rccm TEXT,

    activity TEXT,
    tax_regime TEXT,

    address TEXT,
    phone TEXT,
    email TEXT,

    contact_name TEXT,

    status TEXT NOT NULL DEFAULT 'actif',

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT clients_status_check
    CHECK (
        status IN (
            'actif',
            'inactif',
            'archive'
        )
    )
);


CREATE INDEX idx_clients_cabinet
ON public.clients(cabinet_id);

CREATE INDEX idx_clients_name
ON public.clients(name);

CREATE INDEX idx_clients_ifu
ON public.clients(ifu);


CREATE TRIGGER clients_updated_at
BEFORE UPDATE ON public.clients
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 6. EXERCICES COMPTABLES
-- ============================================================

CREATE TABLE public.exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    client_id UUID NOT NULL
        REFERENCES public.clients(id)
        ON DELETE CASCADE,

    year INTEGER NOT NULL,

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    status TEXT NOT NULL DEFAULT 'ouvert',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT exercises_year_check
    CHECK(year BETWEEN 2000 AND 2100),

    CONSTRAINT exercises_dates_check
    CHECK(end_date >= start_date),

    CONSTRAINT exercises_status_check
    CHECK(
        status IN (
            'ouvert',
            'cloture',
            'archive'
        )
    ),

    CONSTRAINT exercises_unique_year
    UNIQUE(client_id, year)
);


CREATE INDEX idx_exercises_client
ON public.exercises(client_id);

CREATE INDEX idx_exercises_year
ON public.exercises(year);


-- ============================================================
-- 7. DOCUMENTS / FACTURES
-- ============================================================

CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    client_id UUID NOT NULL
        REFERENCES public.clients(id)
        ON DELETE CASCADE,

    exercise_id UUID
        REFERENCES public.exercises(id)
        ON DELETE SET NULL,

    uploaded_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    file_name TEXT NOT NULL,
    storage_path TEXT,

    document_type TEXT NOT NULL DEFAULT 'facture',

    status TEXT NOT NULL DEFAULT 'importe',

    invoice_number TEXT,
    invoice_date DATE,

    supplier_name TEXT,
    supplier_ifu TEXT,

    customer_name TEXT,
    customer_ifu TEXT,

    amount_ht NUMERIC(18,2) NOT NULL DEFAULT 0,
    vat_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    amount_ttc NUMERIC(18,2) NOT NULL DEFAULT 0,

    vat_rate NUMERIC(8,4),

    aib_rate NUMERIC(8,4) NOT NULL DEFAULT 0,
    aib_amount NUMERIC(18,2) NOT NULL DEFAULT 0,

    currency TEXT NOT NULL DEFAULT 'XOF',

    extraction_confidence NUMERIC(5,2),

    extracted_data JSONB NOT NULL DEFAULT '{}'::JSONB,

    ai_notes TEXT,
    validation_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT documents_status_check
    CHECK(
        status IN (
            'importe',
            'analyse',
            'a_controler',
            'valide',
            'rejete',
            'archive'
        )
    ),

    CONSTRAINT documents_amounts_check
    CHECK(
        amount_ht >= 0
        AND vat_amount >= 0
        AND amount_ttc >= 0
        AND aib_amount >= 0
    ),

    CONSTRAINT documents_confidence_check
    CHECK(
        extraction_confidence IS NULL
        OR (
            extraction_confidence >= 0
            AND extraction_confidence <= 100
        )
    )
);


CREATE INDEX idx_documents_cabinet
ON public.documents(cabinet_id);

CREATE INDEX idx_documents_client
ON public.documents(client_id);

CREATE INDEX idx_documents_exercise
ON public.documents(exercise_id);

CREATE INDEX idx_documents_status
ON public.documents(status);

CREATE INDEX idx_documents_invoice_date
ON public.documents(invoice_date);


CREATE TRIGGER documents_updated_at
BEFORE UPDATE ON public.documents
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 8. PLAN COMPTABLE
-- ============================================================

CREATE TABLE public.chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,

    account_class INTEGER,
    account_type TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chart_accounts_unique
    UNIQUE(cabinet_id, account_number)
);


CREATE INDEX idx_chart_accounts_cabinet
ON public.chart_of_accounts(cabinet_id);

CREATE INDEX idx_chart_accounts_number
ON public.chart_of_accounts(account_number);


-- ============================================================
-- 9. JOURNAUX
-- ============================================================

CREATE TABLE public.journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    code TEXT NOT NULL,
    name TEXT NOT NULL,

    journal_type TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT journals_unique_code
    UNIQUE(cabinet_id, code)
);


CREATE INDEX idx_journals_cabinet
ON public.journals(cabinet_id);


-- ============================================================
-- 10. ECRITURES COMPTABLES
-- ============================================================

CREATE TABLE public.accounting_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    client_id UUID NOT NULL
        REFERENCES public.clients(id)
        ON DELETE CASCADE,

    exercise_id UUID
        REFERENCES public.exercises(id)
        ON DELETE SET NULL,

    journal_id UUID
        REFERENCES public.journals(id)
        ON DELETE SET NULL,

    document_id UUID
        REFERENCES public.documents(id)
        ON DELETE SET NULL,

    entry_date DATE NOT NULL,

    reference TEXT,
    label TEXT,

    status TEXT NOT NULL DEFAULT 'brouillon',

    created_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    validated_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    validated_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT accounting_entries_status_check
    CHECK(
        status IN (
            'brouillon',
            'a_valider',
            'validee',
            'rejetee'
        )
    )
);


CREATE INDEX idx_entries_cabinet
ON public.accounting_entries(cabinet_id);

CREATE INDEX idx_entries_client
ON public.accounting_entries(client_id);

CREATE INDEX idx_entries_exercise
ON public.accounting_entries(exercise_id);

CREATE INDEX idx_entries_journal
ON public.accounting_entries(journal_id);

CREATE INDEX idx_entries_date
ON public.accounting_entries(entry_date);


CREATE TRIGGER accounting_entries_updated_at
BEFORE UPDATE ON public.accounting_entries
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 11. LIGNES D'ECRITURES
-- ============================================================

CREATE TABLE public.accounting_entry_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    entry_id UUID NOT NULL
        REFERENCES public.accounting_entries(id)
        ON DELETE CASCADE,

    account_id UUID
        REFERENCES public.chart_of_accounts(id)
        ON DELETE SET NULL,

    account_number TEXT NOT NULL,
    account_name TEXT,

    label TEXT,

    debit NUMERIC(18,2) NOT NULL DEFAULT 0,
    credit NUMERIC(18,2) NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT entry_lines_debit_check
    CHECK(debit >= 0),

    CONSTRAINT entry_lines_credit_check
    CHECK(credit >= 0),

    CONSTRAINT entry_lines_debit_credit_check
    CHECK(
        NOT(debit > 0 AND credit > 0)
    )
);


CREATE INDEX idx_entry_lines_entry
ON public.accounting_entry_lines(entry_id);

CREATE INDEX idx_entry_lines_account
ON public.accounting_entry_lines(account_number);


-- ============================================================
-- 12. DECLARATIONS FISCALES
-- ============================================================

CREATE TABLE public.tax_declarations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    client_id UUID NOT NULL
        REFERENCES public.clients(id)
        ON DELETE CASCADE,

    exercise_id UUID
        REFERENCES public.exercises(id)
        ON DELETE SET NULL,

    declaration_type TEXT NOT NULL,

    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    vat_collected NUMERIC(18,2) NOT NULL DEFAULT 0,
    vat_deductible NUMERIC(18,2) NOT NULL DEFAULT 0,
    vat_payable NUMERIC(18,2) NOT NULL DEFAULT 0,

    aib_amount NUMERIC(18,2) NOT NULL DEFAULT 0,

    status TEXT NOT NULL DEFAULT 'brouillon',

    due_date DATE,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT declarations_status_check
    CHECK(
        status IN (
            'brouillon',
            'a_controler',
            'validee',
            'deposee',
            'archivee'
        )
    ),

    CONSTRAINT declarations_dates_check
    CHECK(period_end >= period_start)
);


CREATE INDEX idx_declarations_client
ON public.tax_declarations(client_id);

CREATE INDEX idx_declarations_period
ON public.tax_declarations(period_start, period_end);

CREATE INDEX idx_declarations_status
ON public.tax_declarations(status);


CREATE TRIGGER tax_declarations_updated_at
BEFORE UPDATE ON public.tax_declarations
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 13. CONTROLES / ANOMALIES
-- ============================================================

CREATE TABLE public.accounting_controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID NOT NULL
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    client_id UUID NOT NULL
        REFERENCES public.clients(id)
        ON DELETE CASCADE,

    document_id UUID
        REFERENCES public.documents(id)
        ON DELETE CASCADE,

    entry_id UUID
        REFERENCES public.accounting_entries(id)
        ON DELETE CASCADE,

    control_type TEXT NOT NULL,

    severity TEXT NOT NULL DEFAULT 'warning',

    title TEXT NOT NULL,
    description TEXT,

    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,

    resolved_by UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT controls_severity_check
    CHECK(
        severity IN (
            'info',
            'warning',
            'error',
            'critical'
        )
    )
);


CREATE INDEX idx_controls_client
ON public.accounting_controls(client_id);

CREATE INDEX idx_controls_document
ON public.accounting_controls(document_id);

CREATE INDEX idx_controls_entry
ON public.accounting_controls(entry_id);

CREATE INDEX idx_controls_open
ON public.accounting_controls(is_resolved);


-- ============================================================
-- 14. AUDIT LOG
-- ============================================================

CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cabinet_id UUID
        REFERENCES public.cabinets(id)
        ON DELETE CASCADE,

    user_id UUID
        REFERENCES auth.users(id)
        ON DELETE SET NULL,

    action TEXT NOT NULL,

    table_name TEXT,
    record_id UUID,

    old_data JSONB,
    new_data JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX idx_audit_cabinet
ON public.audit_logs(cabinet_id);

CREATE INDEX idx_audit_user
ON public.audit_logs(user_id);

CREATE INDEX idx_audit_created
ON public.audit_logs(created_at);


-- ============================================================
-- 15. FONCTION : MEMBRE D'UN CABINET
-- ============================================================

CREATE OR REPLACE FUNCTION public.is_cabinet_member(
    target_cabinet UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.cabinet_members
        WHERE cabinet_id = target_cabinet
        AND user_id = auth.uid()
    );
$$;


-- ============================================================
-- 16. FONCTION : ROLE UTILISATEUR
-- ============================================================

CREATE OR REPLACE FUNCTION public.get_cabinet_role(
    target_cabinet UUID
)
RETURNS TEXT
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role
    FROM public.cabinet_members
    WHERE cabinet_id = target_cabinet
    AND user_id = auth.uid()
    LIMIT 1;
$$;


-- ============================================================
-- 17. RLS
-- ============================================================

ALTER TABLE public.cabinets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cabinet_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_entry_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_declarations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounting_controls ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 18. CABINETS POLICIES
-- ============================================================

CREATE POLICY "cabinet_members_can_view_cabinet"
ON public.cabinets
FOR SELECT
TO authenticated
USING(
    public.is_cabinet_member(id)
);


CREATE POLICY "cabinet_admins_can_update_cabinet"
ON public.cabinets
FOR UPDATE
TO authenticated
USING(
    public.get_cabinet_role(id)
    IN ('admin', 'expert_comptable')
)
WITH CHECK(
    public.get_cabinet_role(id)
    IN ('admin', 'expert_comptable')
);


-- ============================================================
-- 19. MEMBERS POLICIES
-- ============================================================

CREATE POLICY "members_can_view_members"
ON public.cabinet_members
FOR SELECT
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "admins_can_manage_members"
ON public.cabinet_members
FOR ALL
TO authenticated
USING(
    public.get_cabinet_role(cabinet_id)
    IN ('admin', 'expert_comptable')
)
WITH CHECK(
    public.get_cabinet_role(cabinet_id)
    IN ('admin', 'expert_comptable')
);


-- ============================================================
-- 20. CLIENTS POLICIES
-- ============================================================

CREATE POLICY "members_can_view_clients"
ON public.clients
FOR SELECT
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "members_can_insert_clients"
ON public.clients
FOR INSERT
TO authenticated
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "members_can_update_clients"
ON public.clients
FOR UPDATE
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "admins_can_delete_clients"
ON public.clients
FOR DELETE
TO authenticated
USING(
    public.get_cabinet_role(cabinet_id)
    IN ('admin', 'expert_comptable')
);


-- ============================================================
-- 21. EXERCICES POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_exercises"
ON public.exercises
FOR ALL
TO authenticated
USING(
    EXISTS(
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
        AND public.is_cabinet_member(c.cabinet_id)
    )
)
WITH CHECK(
    EXISTS(
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
        AND public.is_cabinet_member(c.cabinet_id)
    )
);


-- ============================================================
-- 22. DOCUMENTS POLICIES
-- ============================================================

CREATE POLICY "members_can_view_documents"
ON public.documents
FOR SELECT
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "members_can_insert_documents"
ON public.documents
FOR INSERT
TO authenticated
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "members_can_update_documents"
ON public.documents
FOR UPDATE
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "admins_can_delete_documents"
ON public.documents
FOR DELETE
TO authenticated
USING(
    public.get_cabinet_role(cabinet_id)
    IN ('admin', 'expert_comptable')
);


-- ============================================================
-- 23. PLAN COMPTABLE POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_accounts"
ON public.chart_of_accounts
FOR ALL
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 24. JOURNAUX POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_journals"
ON public.journals
FOR ALL
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 25. ECRITURES POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_entries"
ON public.accounting_entries
FOR ALL
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 26. LIGNES D'ECRITURES POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_entry_lines"
ON public.accounting_entry_lines
FOR ALL
TO authenticated
USING(
    EXISTS(
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
        AND public.is_cabinet_member(e.cabinet_id)
    )
)
WITH CHECK(
    EXISTS(
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
        AND public.is_cabinet_member(e.cabinet_id)
    )
);


-- ============================================================
-- 27. DECLARATIONS POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_declarations"
ON public.tax_declarations
FOR ALL
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 28. CONTROLES POLICIES
-- ============================================================

CREATE POLICY "members_can_manage_controls"
ON public.accounting_controls
FOR ALL
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
)
WITH CHECK(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 29. AUDIT POLICIES
-- ============================================================

CREATE POLICY "members_can_view_audit"
ON public.audit_logs
FOR SELECT
TO authenticated
USING(
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 30. PERMISSIONS
-- ============================================================

GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO authenticated;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO authenticated;


-- ============================================================
-- 31. VUE DASHBOARD
-- ============================================================

CREATE OR REPLACE VIEW public.client_dashboard
WITH (security_invoker = true)
AS
SELECT
    c.id AS client_id,
    c.cabinet_id,
    c.name,

    COUNT(DISTINCT d.id) AS documents_count,

    COUNT(DISTINCT d.id)
        FILTER (
            WHERE d.status = 'a_controler'
        ) AS documents_to_review,

    COUNT(DISTINCT e.id)
        FILTER (
            WHERE e.status IN ('brouillon', 'a_valider')
        ) AS entries_to_validate,

    COUNT(DISTINCT ac.id)
        FILTER (
            WHERE ac.is_resolved = FALSE
        ) AS open_controls

FROM public.clients c

LEFT JOIN public.documents d
    ON d.client_id = c.id

LEFT JOIN public.accounting_entries e
    ON e.client_id = c.id

LEFT JOIN public.accounting_controls ac
    ON ac.client_id = c.id

WHERE public.is_cabinet_member(c.cabinet_id)

GROUP BY
    c.id,
    c.cabinet_id,
    c.name;


GRANT SELECT
ON public.client_dashboard
TO authenticated;


-- ============================================================
-- 32. FONCTION : SOLDE D'UNE ECRITURE
-- ============================================================

CREATE OR REPLACE FUNCTION public.accounting_entry_balance(
    entry_uuid UUID
)
RETURNS NUMERIC
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        COALESCE(SUM(debit), 0)
        -
        COALESCE(SUM(credit), 0)
    FROM public.accounting_entry_lines l
    JOIN public.accounting_entries e
        ON e.id = l.entry_id
    WHERE l.entry_id = entry_uuid
    AND public.is_cabinet_member(e.cabinet_id);
$$;


-- ============================================================
-- 33. FONCTION : CREER UN CABINET
-- ============================================================
-- Le premier utilisateur peut appeler cette fonction depuis
-- l'application pour créer son cabinet et devenir admin.

CREATE OR REPLACE FUNCTION public.create_cabinet(
    cabinet_name TEXT,
    cabinet_legal_name TEXT DEFAULT NULL,
    cabinet_ifu TEXT DEFAULT NULL,
    cabinet_rccm TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_cabinet_id UUID;
BEGIN

    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Utilisateur non authentifié';
    END IF;

    INSERT INTO public.cabinets (
        name,
        legal_name,
        ifu,
        rccm
    )
    VALUES (
        cabinet_name,
        cabinet_legal_name,
        cabinet_ifu,
        cabinet_rccm
    )
    RETURNING id INTO new_cabinet_id;

    INSERT INTO public.cabinet_members (
        cabinet_id,
        user_id,
        role
    )
    VALUES (
        new_cabinet_id,
        auth.uid(),
        'admin'
    );

    RETURN new_cabinet_id;
END;
$$;


GRANT EXECUTE
ON FUNCTION public.create_cabinet(
    TEXT,
    TEXT,
    TEXT,
    TEXT
)
TO authenticated;

-- ============================================================
-- ONE7 V2.1
-- SECURITE + CONTROLES + AUDIT
-- ============================================================

BEGIN;

-- ============================================================
-- 1. FONCTION : VERIFIER LE ROLE DANS UN CABINET
-- ============================================================

CREATE OR REPLACE FUNCTION public.has_cabinet_role(
    target_cabinet UUID,
    allowed_roles TEXT[]
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.cabinet_members
        WHERE cabinet_id = target_cabinet
          AND user_id = auth.uid()
          AND role = ANY(allowed_roles)
    );
$$;


-- ============================================================
-- 2. FONCTION : L'UTILISATEUR PEUT MODIFIER LE CABINET
-- ============================================================

CREATE OR REPLACE FUNCTION public.can_write_cabinet(
    target_cabinet UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT public.has_cabinet_role(
        target_cabinet,
        ARRAY[
            'admin',
            'expert_comptable',
            'comptable',
            'assistant'
        ]
    );
$$;


-- ============================================================
-- 3. FONCTION : ADMIN / EXPERT COMPTABLE
-- ============================================================

CREATE OR REPLACE FUNCTION public.is_cabinet_admin(
    target_cabinet UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT public.has_cabinet_role(
        target_cabinet,
        ARRAY[
            'admin',
            'expert_comptable'
        ]
    );
$$;


-- ============================================================
-- 4. DOUBLONS DE FACTURES
-- ============================================================

-- Une même facture ne doit normalement pas être enregistrée
-- plusieurs fois pour un même client et fournisseur.

CREATE UNIQUE INDEX IF NOT EXISTS
idx_documents_unique_invoice
ON public.documents (
    client_id,
    LOWER(invoice_number),
    LOWER(COALESCE(supplier_ifu, supplier_name, ''))
)
WHERE invoice_number IS NOT NULL
  AND invoice_number <> '';


-- ============================================================
-- 5. DOCUMENTS : POLICIES PLUS STRICTES
-- ============================================================

DROP POLICY IF EXISTS "members_can_view_documents"
ON public.documents;

DROP POLICY IF EXISTS "members_can_insert_documents"
ON public.documents;

DROP POLICY IF EXISTS "members_can_update_documents"
ON public.documents;

DROP POLICY IF EXISTS "admins_can_delete_documents"
ON public.documents;


CREATE POLICY "documents_select_members"
ON public.documents
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "documents_insert_members"
ON public.documents
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "documents_update_members"
ON public.documents
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


-- Les documents ne sont pas supprimés physiquement.
-- L'application devra utiliser status = 'archive'.

CREATE POLICY "documents_delete_admin"
ON public.documents
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
);


-- ============================================================
-- 6. CLIENTS : POLICIES PLUS STRICTES
-- ============================================================

DROP POLICY IF EXISTS "members_can_view_clients"
ON public.clients;

DROP POLICY IF EXISTS "members_can_insert_clients"
ON public.clients;

DROP POLICY IF EXISTS "members_can_update_clients"
ON public.clients;

DROP POLICY IF EXISTS "admins_can_delete_clients"
ON public.clients;


CREATE POLICY "clients_select_members"
ON public.clients
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "clients_insert_members"
ON public.clients
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "clients_update_members"
ON public.clients
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "clients_delete_admin"
ON public.clients
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
);


-- ============================================================
-- 7. EXERCICES : PROTECTION DES EXERCICES CLOTURES
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_exercises"
ON public.exercises;


CREATE POLICY "exercises_select_members"
ON public.exercises
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
          AND public.is_cabinet_member(c.cabinet_id)
    )
);


CREATE POLICY "exercises_insert_members"
ON public.exercises
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
          AND public.can_write_cabinet(c.cabinet_id)
    )
);


CREATE POLICY "exercises_update_open"
ON public.exercises
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
          AND public.can_write_cabinet(c.cabinet_id)
    )
    AND status = 'ouvert'
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
          AND public.can_write_cabinet(c.cabinet_id)
    )
);


CREATE POLICY "exercises_delete_admin"
ON public.exercises
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.clients c
        WHERE c.id = exercises.client_id
          AND public.is_cabinet_admin(c.cabinet_id)
    )
    AND status = 'ouvert'
);


-- ============================================================
-- 8. PLAN COMPTABLE : ROLE LECTURE SEULE
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_accounts"
ON public.chart_of_accounts;


CREATE POLICY "accounts_select_members"
ON public.chart_of_accounts
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "accounts_write_members"
ON public.chart_of_accounts
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "accounts_update_members"
ON public.chart_of_accounts
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "accounts_delete_admin"
ON public.chart_of_accounts
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
);


-- ============================================================
-- 9. JOURNAUX
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_journals"
ON public.journals;


CREATE POLICY "journals_select_members"
ON public.journals
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "journals_write_members"
ON public.journals
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "journals_update_members"
ON public.journals
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "journals_delete_admin"
ON public.journals
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
);


-- ============================================================
-- 10. ECRITURES COMPTABLES
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_entries"
ON public.accounting_entries;


CREATE POLICY "entries_select_members"
ON public.accounting_entries
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "entries_insert_members"
ON public.accounting_entries
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
    AND (
        exercise_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.exercises ex
            JOIN public.clients cl
              ON cl.id = ex.client_id
            WHERE ex.id = accounting_entries.exercise_id
              AND cl.cabinet_id = accounting_entries.cabinet_id
              AND ex.status = 'ouvert'
        )
    )
);


CREATE POLICY "entries_update_open"
ON public.accounting_entries
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)

    AND (
        exercise_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.exercises ex
            WHERE ex.id = accounting_entries.exercise_id
              AND ex.status = 'ouvert'
        )
    )
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)

    AND (
        exercise_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.exercises ex
            WHERE ex.id = accounting_entries.exercise_id
              AND ex.status = 'ouvert'
        )
    )
);


CREATE POLICY "entries_delete_admin"
ON public.accounting_entries
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
    AND status = 'brouillon'
);


-- ============================================================
-- 11. LIGNES D'ECRITURES
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_entry_lines"
ON public.accounting_entry_lines;


CREATE POLICY "entry_lines_select_members"
ON public.accounting_entry_lines
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
          AND public.is_cabinet_member(e.cabinet_id)
    )
);


CREATE POLICY "entry_lines_insert_members"
ON public.accounting_entry_lines
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
          AND public.can_write_cabinet(e.cabinet_id)
          AND e.status = 'brouillon'
    )
);


CREATE POLICY "entry_lines_update_members"
ON public.accounting_entry_lines
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
          AND public.can_write_cabinet(e.cabinet_id)
          AND e.status = 'brouillon'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
          AND public.can_write_cabinet(e.cabinet_id)
          AND e.status = 'brouillon'
    )
);


CREATE POLICY "entry_lines_delete_admin"
ON public.accounting_entry_lines
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.accounting_entries e
        WHERE e.id = accounting_entry_lines.entry_id
          AND public.is_cabinet_admin(e.cabinet_id)
          AND e.status = 'brouillon'
    )
);


-- ============================================================
-- 12. CONTROLE D'EQUILIBRE DES ECRITURES
-- ============================================================

CREATE OR REPLACE FUNCTION public.validate_accounting_entry(
    target_entry UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    total_debit NUMERIC(18,2);
    total_credit NUMERIC(18,2);
BEGIN

    SELECT
        COALESCE(SUM(debit), 0),
        COALESCE(SUM(credit), 0)
    INTO
        total_debit,
        total_credit
    FROM public.accounting_entry_lines
    WHERE entry_id = target_entry;

    RETURN (
        total_debit = total_credit
        AND total_debit > 0
    );

END;
$$;


-- ============================================================
-- 13. EMPECHER LA VALIDATION D'UNE ECRITURE DESEQUILIBREE
-- ============================================================

CREATE OR REPLACE FUNCTION public.check_entry_before_validation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN

    IF NEW.status = 'validee'
       AND OLD.status <> 'validee'
    THEN

        IF NOT public.validate_accounting_entry(NEW.id) THEN

            RAISE EXCEPTION
                'Impossible de valider cette écriture : les totaux débit/crédit ne sont pas équilibrés.';

        END IF;

    END IF;

    RETURN NEW;

END;
$$;


DROP TRIGGER IF EXISTS validate_entry_before_update
ON public.accounting_entries;


CREATE TRIGGER validate_entry_before_update
BEFORE UPDATE ON public.accounting_entries
FOR EACH ROW
EXECUTE FUNCTION public.check_entry_before_validation();


-- ============================================================
-- 14. DECLARATIONS FISCALES
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_declarations"
ON public.tax_declarations;


CREATE POLICY "declarations_select_members"
ON public.tax_declarations
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "declarations_insert_members"
ON public.tax_declarations
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "declarations_update_members"
ON public.tax_declarations
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
    AND status NOT IN ('deposee', 'archivee')
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "declarations_delete_admin"
ON public.tax_declarations
FOR DELETE
TO authenticated
USING (
    public.is_cabinet_admin(cabinet_id)
    AND status = 'brouillon'
);


-- ============================================================
-- 15. CONTROLES / ANOMALIES
-- ============================================================

DROP POLICY IF EXISTS "members_can_manage_controls"
ON public.accounting_controls;


CREATE POLICY "controls_select_members"
ON public.accounting_controls
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


CREATE POLICY "controls_write_members"
ON public.accounting_controls
FOR INSERT
TO authenticated
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


CREATE POLICY "controls_update_members"
ON public.accounting_controls
FOR UPDATE
TO authenticated
USING (
    public.can_write_cabinet(cabinet_id)
)
WITH CHECK (
    public.can_write_cabinet(cabinet_id)
);


-- ============================================================
-- 16. AUDIT LOG
-- ============================================================

DROP POLICY IF EXISTS "members_can_view_audit"
ON public.audit_logs;


CREATE POLICY "audit_select_members"
ON public.audit_logs
FOR SELECT
TO authenticated
USING (
    public.is_cabinet_member(cabinet_id)
);


-- ============================================================
-- 17. FONCTION D'AUDIT AUTOMATIQUE
-- ============================================================

CREATE OR REPLACE FUNCTION public.write_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    row_data JSONB;
    target_cabinet UUID;
    target_record UUID;
    audit_action TEXT;
BEGIN

    IF TG_OP = 'DELETE' THEN
        row_data := to_jsonb(OLD);
        target_cabinet := (row_data ->> 'cabinet_id')::UUID;
        target_record := (row_data ->> 'id')::UUID;
        audit_action := 'delete';

    ELSIF TG_OP = 'UPDATE' THEN
        row_data := to_jsonb(NEW);
        target_cabinet := (row_data ->> 'cabinet_id')::UUID;
        target_record := (row_data ->> 'id')::UUID;
        audit_action := 'update';

    ELSE
        row_data := to_jsonb(NEW);
        target_cabinet := (row_data ->> 'cabinet_id')::UUID;
        target_record := (row_data ->> 'id')::UUID;
        audit_action := 'create';
    END IF;


    INSERT INTO public.audit_logs (
        cabinet_id,
        user_id,
        action,
        table_name,
        record_id,
        old_data,
        new_data
    )
    VALUES (
        target_cabinet,
        auth.uid(),
        audit_action,
        TG_TABLE_NAME,
        target_record,
        CASE
            WHEN TG_OP IN ('UPDATE', 'DELETE')
            THEN to_jsonb(OLD)
            ELSE NULL
        END,
        CASE
            WHEN TG_OP IN ('INSERT', 'UPDATE')
            THEN to_jsonb(NEW)
            ELSE NULL
        END
    );

    RETURN COALESCE(NEW, OLD);

END;
$$;


-- ============================================================
-- 18. TRIGGERS AUDIT
-- ============================================================

DROP TRIGGER IF EXISTS audit_clients
ON public.clients;

CREATE TRIGGER audit_clients
AFTER INSERT OR UPDATE OR DELETE
ON public.clients
FOR EACH ROW
EXECUTE FUNCTION public.write_audit_log();


DROP TRIGGER IF EXISTS audit_documents
ON public.documents;

CREATE TRIGGER audit_documents
AFTER INSERT OR UPDATE OR DELETE
ON public.documents
FOR EACH ROW
EXECUTE FUNCTION public.write_audit_log();


DROP TRIGGER IF EXISTS audit_accounting_entries
ON public.accounting_entries;

CREATE TRIGGER audit_accounting_entries
AFTER INSERT OR UPDATE OR DELETE
ON public.accounting_entries
FOR EACH ROW
EXECUTE FUNCTION public.write_audit_log();


DROP TRIGGER IF EXISTS audit_tax_declarations
ON public.tax_declarations;

CREATE TRIGGER audit_tax_declarations
AFTER INSERT OR UPDATE OR DELETE
ON public.tax_declarations
FOR EACH ROW
EXECUTE FUNCTION public.write_audit_log();


-- ============================================================
-- 19. INDEX SUPPLEMENTAIRES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_documents_supplier
ON public.documents(supplier_name);

CREATE INDEX IF NOT EXISTS idx_documents_supplier_ifu
ON public.documents(supplier_ifu);

CREATE INDEX IF NOT EXISTS idx_documents_created
ON public.documents(created_at);

CREATE INDEX IF NOT EXISTS idx_entries_status
ON public.accounting_entries(status);

CREATE INDEX IF NOT EXISTS idx_declarations_due_date
ON public.tax_declarations(due_date);

CREATE INDEX IF NOT EXISTS idx_controls_severity
ON public.accounting_controls(severity);


-- ============================================================
-- 20. SECURITE DES FONCTIONS
-- ============================================================

REVOKE ALL
ON FUNCTION public.has_cabinet_role(UUID, TEXT[])
FROM PUBLIC;

GRANT EXECUTE
ON FUNCTION public.has_cabinet_role(UUID, TEXT[])
TO authenticated;


REVOKE ALL
ON FUNCTION public.can_write_cabinet(UUID)
FROM PUBLIC;

GRANT EXECUTE
ON FUNCTION public.can_write_cabinet(UUID)
TO authenticated;


REVOKE ALL
ON FUNCTION public.is_cabinet_admin(UUID)
FROM PUBLIC;

GRANT EXECUTE
ON FUNCTION public.is_cabinet_admin(UUID)
TO authenticated;


REVOKE ALL
ON FUNCTION public.validate_accounting_entry(UUID)
FROM PUBLIC;

GRANT EXECUTE
ON FUNCTION public.validate_accounting_entry(UUID)
TO authenticated;

-- ============================================================
-- ONE7 V2.2 — DURCISSEMENT MULTI-CABINET
-- ============================================================

REVOKE ALL ON FUNCTION public.is_cabinet_member(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_cabinet_member(UUID) TO authenticated;
REVOKE ALL ON FUNCTION public.get_cabinet_role(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_cabinet_role(UUID) TO authenticated;
REVOKE ALL ON FUNCTION public.create_cabinet(TEXT, TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.create_cabinet(TEXT, TEXT, TEXT, TEXT) TO authenticated;

CREATE OR REPLACE FUNCTION public.check_one7_tenant_integrity()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    IF TG_TABLE_NAME = 'documents' THEN
        IF NOT EXISTS (SELECT 1 FROM public.clients c WHERE c.id=NEW.client_id AND c.cabinet_id=NEW.cabinet_id) THEN
            RAISE EXCEPTION 'Document incohérent : le client n''appartient pas au cabinet.';
        END IF;
        IF NEW.exercise_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.exercises ex JOIN public.clients c ON c.id=ex.client_id
            WHERE ex.id=NEW.exercise_id AND ex.client_id=NEW.client_id AND c.cabinet_id=NEW.cabinet_id
        ) THEN RAISE EXCEPTION 'Document incohérent : exercice/client/cabinet incompatibles.'; END IF;
    ELSIF TG_TABLE_NAME = 'accounting_entries' THEN
        IF NOT EXISTS (SELECT 1 FROM public.clients c WHERE c.id=NEW.client_id AND c.cabinet_id=NEW.cabinet_id) THEN
            RAISE EXCEPTION 'Écriture incohérente : le client n''appartient pas au cabinet.';
        END IF;
        IF NEW.exercise_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.exercises ex WHERE ex.id=NEW.exercise_id AND ex.client_id=NEW.client_id) THEN
            RAISE EXCEPTION 'Écriture incohérente : l''exercice n''appartient pas au client.';
        END IF;
        IF NEW.journal_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.journals j WHERE j.id=NEW.journal_id AND j.cabinet_id=NEW.cabinet_id) THEN
            RAISE EXCEPTION 'Écriture incohérente : le journal n''appartient pas au cabinet.';
        END IF;
        IF NEW.document_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM public.documents d WHERE d.id=NEW.document_id AND d.cabinet_id=NEW.cabinet_id AND d.client_id=NEW.client_id
        ) THEN RAISE EXCEPTION 'Écriture incohérente : le document n''appartient pas au cabinet/client.'; END IF;
    ELSIF TG_TABLE_NAME = 'tax_declarations' THEN
        IF NOT EXISTS (SELECT 1 FROM public.clients c WHERE c.id=NEW.client_id AND c.cabinet_id=NEW.cabinet_id) THEN
            RAISE EXCEPTION 'Déclaration incohérente : le client n''appartient pas au cabinet.';
        END IF;
        IF NEW.exercise_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.exercises ex WHERE ex.id=NEW.exercise_id AND ex.client_id=NEW.client_id) THEN
            RAISE EXCEPTION 'Déclaration incohérente : l''exercice n''appartient pas au client.';
        END IF;
    ELSIF TG_TABLE_NAME = 'accounting_controls' THEN
        IF NOT EXISTS (SELECT 1 FROM public.clients c WHERE c.id=NEW.client_id AND c.cabinet_id=NEW.cabinet_id) THEN
            RAISE EXCEPTION 'Contrôle incohérent : le client n''appartient pas au cabinet.';
        END IF;
        IF NEW.document_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.documents d WHERE d.id=NEW.document_id AND d.cabinet_id=NEW.cabinet_id AND d.client_id=NEW.client_id) THEN
            RAISE EXCEPTION 'Contrôle incohérent : le document n''appartient pas au cabinet/client.';
        END IF;
        IF NEW.entry_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.accounting_entries e WHERE e.id=NEW.entry_id AND e.cabinet_id=NEW.cabinet_id AND e.client_id=NEW.client_id) THEN
            RAISE EXCEPTION 'Contrôle incohérent : l''écriture n''appartient pas au cabinet/client.';
        END IF;
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS documents_tenant_integrity ON public.documents;
CREATE TRIGGER documents_tenant_integrity BEFORE INSERT OR UPDATE ON public.documents FOR EACH ROW EXECUTE FUNCTION public.check_one7_tenant_integrity();
DROP TRIGGER IF EXISTS entries_tenant_integrity ON public.accounting_entries;
CREATE TRIGGER entries_tenant_integrity BEFORE INSERT OR UPDATE ON public.accounting_entries FOR EACH ROW EXECUTE FUNCTION public.check_one7_tenant_integrity();
DROP TRIGGER IF EXISTS declarations_tenant_integrity ON public.tax_declarations;
CREATE TRIGGER declarations_tenant_integrity BEFORE INSERT OR UPDATE ON public.tax_declarations FOR EACH ROW EXECUTE FUNCTION public.check_one7_tenant_integrity();
DROP TRIGGER IF EXISTS controls_tenant_integrity ON public.accounting_controls;
CREATE TRIGGER controls_tenant_integrity BEFORE INSERT OR UPDATE ON public.accounting_controls FOR EACH ROW EXECUTE FUNCTION public.check_one7_tenant_integrity();

CREATE OR REPLACE FUNCTION public.check_entry_line_account_integrity()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE entry_cabinet UUID;
BEGIN
    SELECT cabinet_id INTO entry_cabinet FROM public.accounting_entries WHERE id=NEW.entry_id;
    IF entry_cabinet IS NULL THEN RAISE EXCEPTION 'Écriture introuvable.'; END IF;
    IF NEW.account_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM public.chart_of_accounts a WHERE a.id=NEW.account_id AND a.cabinet_id=entry_cabinet
    ) THEN RAISE EXCEPTION 'Compte comptable incompatible avec le cabinet de l''écriture.'; END IF;
    RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS entry_lines_account_integrity ON public.accounting_entry_lines;
CREATE TRIGGER entry_lines_account_integrity BEFORE INSERT OR UPDATE ON public.accounting_entry_lines FOR EACH ROW EXECUTE FUNCTION public.check_entry_line_account_integrity();

CREATE OR REPLACE FUNCTION public.validate_accounting_entry(target_entry UUID)
RETURNS BOOLEAN LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE total_debit NUMERIC(18,2); total_credit NUMERIC(18,2); target_cabinet UUID;
BEGIN
    SELECT cabinet_id INTO target_cabinet FROM public.accounting_entries WHERE id=target_entry;
    IF target_cabinet IS NULL OR NOT public.is_cabinet_member(target_cabinet) THEN RETURN FALSE; END IF;
    SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) INTO total_debit,total_credit
    FROM public.accounting_entry_lines WHERE entry_id=target_entry;
    RETURN total_debit=total_credit AND total_debit>0;
END; $$;
REVOKE ALL ON FUNCTION public.validate_accounting_entry(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.validate_accounting_entry(UUID) TO authenticated;

CREATE OR REPLACE VIEW public.client_dashboard WITH (security_invoker=true) AS
SELECT c.id AS client_id,c.cabinet_id,c.name,
COUNT(DISTINCT d.id) AS documents_count,
COUNT(DISTINCT d.id) FILTER (WHERE d.status='a_controler') AS documents_to_review,
COUNT(DISTINCT e.id) FILTER (WHERE e.status IN ('brouillon','a_valider')) AS entries_to_validate,
COUNT(DISTINCT ac.id) FILTER (WHERE ac.is_resolved=FALSE) AS open_controls
FROM public.clients c
LEFT JOIN public.documents d ON d.client_id=c.id AND d.cabinet_id=c.cabinet_id
LEFT JOIN public.accounting_entries e ON e.client_id=c.id AND e.cabinet_id=c.cabinet_id
LEFT JOIN public.accounting_controls ac ON ac.client_id=c.id AND ac.cabinet_id=c.cabinet_id
WHERE public.is_cabinet_member(c.cabinet_id)
GROUP BY c.id,c.cabinet_id,c.name;
GRANT SELECT ON public.client_dashboard TO authenticated;

CREATE INDEX IF NOT EXISTS idx_documents_client_status ON public.documents(client_id,status);
CREATE INDEX IF NOT EXISTS idx_entries_client_status ON public.accounting_entries(client_id,status);
CREATE INDEX IF NOT EXISTS idx_declarations_client_status ON public.tax_declarations(client_id,status);
CREATE INDEX IF NOT EXISTS idx_controls_client_resolved ON public.accounting_controls(client_id,is_resolved);

COMMIT;

-- ONE7 V2.2
-- PARAMETRES CABINET
-- Migration indépendante du schéma V2/V2.1

BEGIN;

CREATE TABLE IF NOT EXISTS public.cabinet_settings (
    cabinet_id uuid PRIMARY KEY REFERENCES public.cabinets(id) ON DELETE CASCADE,
    vat_default_rate numeric(8,4) NOT NULL DEFAULT 18,
    aib_default_rate numeric(8,4) NOT NULL DEFAULT 1,
    ai_enabled boolean NOT NULL DEFAULT false,
    ai_auto_analysis boolean NOT NULL DEFAULT false,
    settings jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cabinet_settings_vat_rate_ck CHECK (vat_default_rate >= 0 AND vat_default_rate <= 100),
    CONSTRAINT cabinet_settings_aib_rate_ck CHECK (aib_default_rate >= 0 AND aib_default_rate <= 100)
);

CREATE OR REPLACE FUNCTION public.ensure_cabinet_settings()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.cabinet_settings (cabinet_id)
    VALUES (NEW.id)
    ON CONFLICT (cabinet_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cabinet_settings_after_insert ON public.cabinets;
CREATE TRIGGER trg_cabinet_settings_after_insert
AFTER INSERT ON public.cabinets
FOR EACH ROW EXECUTE FUNCTION public.ensure_cabinet_settings();

CREATE OR REPLACE FUNCTION public.set_cabinet_settings_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cabinet_settings_updated_at ON public.cabinet_settings;
CREATE TRIGGER trg_cabinet_settings_updated_at
BEFORE UPDATE ON public.cabinet_settings
FOR EACH ROW EXECUTE FUNCTION public.set_cabinet_settings_updated_at();

ALTER TABLE public.cabinet_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cabinet_settings_select ON public.cabinet_settings;
CREATE POLICY cabinet_settings_select
ON public.cabinet_settings
FOR SELECT
TO authenticated
USING (public.is_cabinet_member(cabinet_id));

DROP POLICY IF EXISTS cabinet_settings_insert ON public.cabinet_settings;
CREATE POLICY cabinet_settings_insert
ON public.cabinet_settings
FOR INSERT
TO authenticated
WITH CHECK (public.can_write_cabinet(cabinet_id));

DROP POLICY IF EXISTS cabinet_settings_update ON public.cabinet_settings;
CREATE POLICY cabinet_settings_update
ON public.cabinet_settings
FOR UPDATE
TO authenticated
USING (public.can_write_cabinet(cabinet_id))
WITH CHECK (public.can_write_cabinet(cabinet_id));

INSERT INTO public.cabinet_settings (cabinet_id)
SELECT id FROM public.cabinets
ON CONFLICT (cabinet_id) DO NOTHING;

GRANT SELECT, INSERT, UPDATE ON public.cabinet_settings TO authenticated;

COMMIT;

# ============================================================
# ONE7 V2.2
# database.py
# ============================================================

from functools import lru_cache
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Iterable

from supabase import create_client, Client

from config import get_supabase_url, get_supabase_key


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Crée et valide une instance du client Supabase.

    Certaines combinaisons de versions/compatibilités peuvent renvoyer
    un tuple au lieu du client attendu. One7 récupère alors l'objet qui
    expose l'interface Auth (.auth) afin d'éviter l'erreur :
    "'tuple' object has no attribute 'auth'".
    """
    url = get_supabase_url()
    key = get_supabase_key()

    if not url or not isinstance(url, str):
        raise RuntimeError("SUPABASE_URL est vide ou invalide.")
    if not key or not isinstance(key, str):
        raise RuntimeError("SUPABASE_KEY est vide ou invalide.")

    raw_client = create_client(url.strip(), key.strip())

        # ============================================================
    # DIAGNOSTIC SUPABASE — TEMPORAIRE
    # ============================================================
    try:
        import supabase as supabase_module
        from importlib.metadata import version as package_version

        print("========== ONE7 SUPABASE DIAGNOSTIC ==========")
        print("SUPABASE PACKAGE VERSION :", package_version("supabase"))
        print("SUPABASE MODULE :", supabase_module.__file__)
        print("CLIENT TYPE :", type(raw_client))
        print("CLIENT MODULE :", type(raw_client).__module__)
        print("CLIENT CLASS :", type(raw_client).__name__)
        print("HAS AUTH :", hasattr(raw_client, "auth"))

        auth_names = [
            name for name in dir(raw_client)
            if "auth" in name.lower()
        ]

        print("AUTH-RELATED ATTRIBUTES :", auth_names)
        print("HAS POSTGREST :", hasattr(raw_client, "postgrest"))
        print("HAS STORAGE :", hasattr(raw_client, "storage"))
        print("HAS FUNCTIONS :", hasattr(raw_client, "functions"))
        print("HAS REALTIME :", hasattr(raw_client, "realtime"))
        print("================================================")
    except Exception as diagnostic_error:
        print(
            "ONE7 SUPABASE DIAGNOSTIC ERROR :",
            repr(diagnostic_error)
        )

    if hasattr(raw_client, "auth"):
        return raw_client

    if isinstance(raw_client, tuple):
        for item in raw_client:
            if hasattr(item, "auth"):
                return item

    raise RuntimeError(
        "Le client Supabase retourné n'expose pas l'interface Auth (.auth). "
        "Vérifiez la version du package supabase installée sur Streamlit Cloud."
    )


def get_current_user():
    try:
        response = get_supabase().auth.get_user()
        return response.user if response else None
    except Exception:
        return None


def get_current_session():
    try:
        return get_supabase().auth.get_session()
    except Exception:
        return None


def sign_out():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass


def get_cabinet_id(cabinet: Optional[Dict[str, Any]]) -> Optional[str]:
    return cabinet.get("id") if cabinet else None


def _safe_limit(limit: int, maximum: int = 100) -> int:
    return max(1, min(int(limit), maximum))


def _count(table: str, *filters) -> int:
    try:
        query = get_supabase().table(table).select("id", count="exact", head=True)
        for column, value in filters:
            query = query.eq(column, value)
        response = query.execute()
        return int(response.count or 0)
    except Exception:
        return 0


# ============================================================
# DASHBOARD
# ============================================================

def get_dashboard_stats(cabinet_id: Optional[str]) -> Dict[str, int]:
    empty = {
        "clients": 0,
        "documents": 0,
        "documents_a_controler": 0,
        "documents_importes": 0,
        "ecritures": 0,
        "ecritures_a_valider": 0,
        "anomalies": 0,
        "anomalies_critiques": 0,
        "declarations_a_controler": 0,
        "declarations_en_retard": 0,
    }
    if not cabinet_id:
        return empty

    stats = dict(empty)
    stats["clients"] = _count("clients", ("cabinet_id", cabinet_id), ("status", "actif"))
    stats["documents"] = _count("documents", ("cabinet_id", cabinet_id))
    stats["documents_a_controler"] = _count("documents", ("cabinet_id", cabinet_id), ("status", "a_controler"))
    stats["documents_importes"] = _count("documents", ("cabinet_id", cabinet_id), ("status", "importe"))
    stats["ecritures"] = _count("accounting_entries", ("cabinet_id", cabinet_id))
    stats["ecritures_a_valider"] = _count("accounting_entries", ("cabinet_id", cabinet_id), ("status", "a_valider"))
    stats["anomalies"] = _count("accounting_controls", ("cabinet_id", cabinet_id), ("is_resolved", False))
    stats["anomalies_critiques"] = _count("accounting_controls", ("cabinet_id", cabinet_id), ("is_resolved", False), ("severity", "critical"))
    stats["declarations_a_controler"] = _count("tax_declarations", ("cabinet_id", cabinet_id), ("status", "a_controler"))

    try:
        response = (
            get_supabase().table("tax_declarations")
            .select("id", count="exact", head=True)
            .eq("cabinet_id", cabinet_id)
            .in_("status", ["brouillon", "a_controler"])
            .lt("due_date", date.today().isoformat())
            .execute()
        )
        stats["declarations_en_retard"] = int(response.count or 0)
    except Exception:
        pass
    return stats


def get_recent_documents(cabinet_id: Optional[str], limit: int = 5):
    if not cabinet_id:
        return []
    try:
        response = (
            get_supabase().table("documents")
            .select("id,file_name,document_type,status,invoice_number,invoice_date,amount_ttc,created_at,clients(name)")
            .eq("cabinet_id", cabinet_id)
            .order("created_at", desc=True)
            .limit(_safe_limit(limit, 20))
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def get_open_controls(cabinet_id: Optional[str], limit: int = 5):
    if not cabinet_id:
        return []
    try:
        response = (
            get_supabase().table("accounting_controls")
            .select("id,severity,title,description,is_resolved,created_at,clients(name)")
            .eq("cabinet_id", cabinet_id)
            .eq("is_resolved", False)
            .order("created_at", desc=True)
            .limit(_safe_limit(limit, 20))
            .execute()
        )
        return response.data or []
    except Exception:
        return []


# ============================================================
# CLIENTS / EXERCICES
# ============================================================

def get_clients(cabinet_id: Optional[str], status: Optional[str] = None):
    if not cabinet_id:
        return []
    try:
        query = (
            get_supabase().table("clients")
            .select("id,cabinet_id,name,legal_name,ifu,rccm,activity,tax_regime,address,phone,email,contact_name,status,notes,created_at,updated_at")
            .eq("cabinet_id", cabinet_id)
            .order("name")
        )
        if status:
            query = query.eq("status", status)
        return query.execute().data or []
    except Exception:
        return []


def create_client(cabinet_id: str, name: str, legal_name: str = "", ifu: str = "", rccm: str = "", activity: str = "", tax_regime: str = "", address: str = "", phone: str = "", email: str = "", contact_name: str = "", notes: str = ""):
    if not cabinet_id:
        return False, "Cabinet introuvable."
    if not name or not name.strip():
        return False, "Le nom du client est obligatoire."
    payload = {
        "cabinet_id": cabinet_id,
        "name": name.strip(),
        "legal_name": legal_name.strip() or None,
        "ifu": ifu.strip() or None,
        "rccm": rccm.strip() or None,
        "activity": activity.strip() or None,
        "tax_regime": tax_regime.strip() or None,
        "address": address.strip() or None,
        "phone": phone.strip() or None,
        "email": email.strip() or None,
        "contact_name": contact_name.strip() or None,
        "notes": notes.strip() or None,
        "status": "actif",
    }
    try:
        data = get_supabase().table("clients").insert(payload).execute().data
        return (True, "Client créé avec succès.") if data else (False, "La création du client a échoué.")
    except Exception as exc:
        return False, str(exc)


def update_client(client_id: str, cabinet_id: str, values: Dict[str, Any]):
    allowed = {"status", "phone", "email", "address", "notes"}
    payload = {k: v for k, v in values.items() if k in allowed}
    if not client_id or not cabinet_id:
        return False, "Client ou cabinet introuvable."
    if not payload:
        return False, "Aucune modification à enregistrer."
    try:
        data = get_supabase().table("clients").update(payload).eq("id", client_id).eq("cabinet_id", cabinet_id).execute().data
        return (True, "Client mis à jour avec succès.") if data else (False, "Aucune modification n'a été enregistrée.")
    except Exception as exc:
        return False, str(exc)


def get_client_exercises(client_id: Optional[str]):
    if not client_id:
        return []
    try:
        return (
            get_supabase().table("exercises")
            .select("id,client_id,year,start_date,end_date,status,created_at")
            .eq("client_id", client_id)
            .order("year", desc=True)
            .execute().data or []
        )
    except Exception:
        return []


def create_exercise(client_id: str, year: int, start_date, end_date):
    if not client_id:
        return False, "Client introuvable."
    if end_date < start_date:
        return False, "La date de fin doit être postérieure ou égale à la date de début."
    payload = {"client_id": client_id, "year": int(year), "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "status": "ouvert"}
    try:
        data = get_supabase().table("exercises").insert(payload).execute().data
        return (True, "Exercice créé avec succès.") if data else (False, "La création de l'exercice a échoué.")
    except Exception as exc:
        message = str(exc)
        if "exercises_unique_year" in message or "duplicate key" in message.lower():
            return False, "Un exercice existe déjà pour cette année et ce client."
        return False, message


# ============================================================
# DOCUMENTS
# ============================================================

def get_documents(cabinet_id: Optional[str], client_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    """Liste les documents du cabinet avec filtres optionnels."""
    if not cabinet_id:
        return []
    try:
        query = (
            get_supabase().table("documents")
            .select("id,cabinet_id,client_id,exercise_id,uploaded_by,file_name,storage_path,document_type,status,invoice_number,invoice_date,supplier_name,supplier_ifu,customer_name,customer_ifu,amount_ht,vat_amount,amount_ttc,vat_rate,aib_rate,aib_amount,currency,extraction_confidence,extracted_data,ai_notes,validation_notes,created_at,updated_at,clients(name),exercises(year)")
            .eq("cabinet_id", cabinet_id)
            .order("created_at", desc=True)
            .limit(_safe_limit(limit))
        )
        if client_id:
            query = query.eq("client_id", client_id)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []
    except Exception:
        return []


def find_duplicate_document(cabinet_id: str, client_id: str, invoice_number: Optional[str], supplier_ifu: Optional[str] = None, supplier_name: Optional[str] = None):
    """Recherche un doublon avant insertion, en miroir de l'index SQL V2.1."""
    if not cabinet_id or not client_id or not invoice_number or not invoice_number.strip():
        return None
    try:
        query = (
            get_supabase().table("documents")
            .select("id,file_name,invoice_number,supplier_name,supplier_ifu,amount_ttc,status,created_at")
            .eq("cabinet_id", cabinet_id)
            .eq("client_id", client_id)
            .ilike("invoice_number", invoice_number.strip())
            .limit(20)
        )
        rows = query.execute().data or []
        supplier_key = (supplier_ifu or supplier_name or "").strip().lower()
        for row in rows:
            row_key = (row.get("supplier_ifu") or row.get("supplier_name") or "").strip().lower()
            if row_key == supplier_key:
                return row
        return None
    except Exception:
        return None


def create_document(cabinet_id: str, client_id: str, file_name: str, storage_path: Optional[str] = None, exercise_id: Optional[str] = None, uploaded_by: Optional[str] = None, document_type: str = "facture", status: str = "importe", fields: Optional[Dict[str, Any]] = None):
    """Insère un document. La sécurité finale est assurée par RLS + contraintes SQL."""
    if not cabinet_id or not client_id or not file_name:
        return False, None, "Cabinet, client et nom de fichier sont obligatoires."

    allowed_statuses = {"importe", "analyse", "a_controler", "valide", "rejete", "archive"}
    if status not in allowed_statuses:
        status = "importe"

    fields = fields or {}
    payload = {
        "cabinet_id": cabinet_id,
        "client_id": client_id,
        "exercise_id": exercise_id,
        "uploaded_by": uploaded_by,
        "file_name": file_name,
        "storage_path": storage_path,
        "document_type": document_type or "facture",
        "status": status,
        "invoice_number": fields.get("invoice_number"),
        "invoice_date": fields.get("invoice_date"),
        "supplier_name": fields.get("supplier_name"),
        "supplier_ifu": fields.get("supplier_ifu"),
        "customer_name": fields.get("customer_name"),
        "customer_ifu": fields.get("customer_ifu"),
        "amount_ht": fields.get("amount_ht", 0) or 0,
        "vat_amount": fields.get("vat_amount", 0) or 0,
        "amount_ttc": fields.get("amount_ttc", 0) or 0,
        "vat_rate": fields.get("vat_rate"),
        "aib_rate": fields.get("aib_rate", 0) or 0,
        "aib_amount": fields.get("aib_amount", 0) or 0,
        "currency": fields.get("currency") or "XOF",
        "extraction_confidence": fields.get("extraction_confidence"),
        "extracted_data": fields.get("extracted_data") or {},
        "ai_notes": fields.get("ai_notes"),
        "validation_notes": fields.get("validation_notes"),
    }
    # Ne pas envoyer de clés NULL inutiles pour certains champs facultatifs.
    payload = {k: v for k, v in payload.items() if v is not None or k in {"exercise_id", "uploaded_by", "storage_path"}}

    try:
        data = get_supabase().table("documents").insert(payload).execute().data
        if data:
            return True, data[0], "Document enregistré avec succès."
        return False, None, "Le document n'a pas été enregistré."
    except Exception as exc:
        message = str(exc)
        if "idx_documents_unique_invoice" in message or "duplicate key" in message.lower():
            return False, None, "Doublon détecté : ce numéro de facture existe déjà pour ce fournisseur et ce client."
        return False, None, message


def update_document(document_id: str, cabinet_id: str, values: Dict[str, Any]):
    allowed = {
        "status", "document_type", "invoice_number", "invoice_date", "supplier_name", "supplier_ifu",
        "customer_name", "customer_ifu", "amount_ht", "vat_amount", "amount_ttc", "vat_rate",
        "aib_rate", "aib_amount", "currency", "extraction_confidence", "extracted_data", "ai_notes", "validation_notes", "exercise_id"
    }
    payload = {k: v for k, v in values.items() if k in allowed}
    if not document_id or not cabinet_id or not payload:
        return False, "Aucune modification à enregistrer."
    try:
        data = get_supabase().table("documents").update(payload).eq("id", document_id).eq("cabinet_id", cabinet_id).execute().data
        return (True, "Document mis à jour avec succès.") if data else (False, "Aucune modification n'a été enregistrée.")
    except Exception as exc:
        return False, str(exc)


def archive_document(document_id: str, cabinet_id: str):
    return update_document(document_id, cabinet_id, {"status": "archive"})


def upload_document_file(storage_path: str, file_bytes: bytes, content_type: str):
    """Dépose le fichier dans le bucket privé 'documents'."""
    try:
        result = get_supabase().storage.from_("documents").upload(
            storage_path,
            file_bytes,
            {"content-type": content_type, "upsert": "false"},
        )
        return True, result
    except Exception as exc:
        return False, str(exc)


def remove_document_file(storage_path: str):
    if not storage_path:
        return True, None
    try:
        result = get_supabase().storage.from_("documents").remove([storage_path])
        return True, result
    except Exception as exc:
        return False, str(exc)

# ============================================================
# COMPTABILITE — PLAN COMPTABLE / JOURNAUX / ECRITURES
# ============================================================

def get_chart_of_accounts(cabinet_id: Optional[str], search: Optional[str] = None, active_only: bool = True, limit: int = 500):
    if not cabinet_id:
        return []
    try:
        query = (get_supabase().table("chart_of_accounts")
                 .select("id,cabinet_id,account_number,account_name,account_class,account_type,is_active,created_at")
                 .eq("cabinet_id", cabinet_id)
                 .order("account_number")
                 .limit(_safe_limit(limit)))
        if active_only:
            query = query.eq("is_active", True)
        if search:
            term = search.strip()
            if term:
                query = query.or_(f"account_number.ilike.%{term}%,account_name.ilike.%{term}%")
        return query.execute().data or []
    except Exception:
        return []


def create_chart_account(cabinet_id: str, account_number: str, account_name: str,
                         account_class: Optional[int] = None, account_type: Optional[str] = None):
    if not cabinet_id or not account_number.strip() or not account_name.strip():
        return False, "Le numéro et le libellé du compte sont obligatoires."
    payload = {
        "cabinet_id": cabinet_id,
        "account_number": account_number.strip(),
        "account_name": account_name.strip(),
        "account_class": account_class,
        "account_type": account_type.strip() if isinstance(account_type, str) and account_type.strip() else None,
        "is_active": True,
    }
    try:
        data = get_supabase().table("chart_of_accounts").insert(payload).execute().data
        return (True, "Compte créé avec succès.") if data else (False, "La création du compte a échoué.")
    except Exception as exc:
        msg = str(exc)
        if "chart_accounts_unique" in msg or "duplicate key" in msg.lower():
            return False, "Ce numéro de compte existe déjà dans ce cabinet."
        return False, msg


def update_chart_account(account_id: str, cabinet_id: str, values: Dict[str, Any]):
    allowed = {"account_name", "account_class", "account_type", "is_active"}
    payload = {k: v for k, v in values.items() if k in allowed}
    if not account_id or not cabinet_id or not payload:
        return False, "Aucune modification à enregistrer."
    try:
        data = (get_supabase().table("chart_of_accounts").update(payload)
                .eq("id", account_id).eq("cabinet_id", cabinet_id).execute().data)
        return (True, "Compte mis à jour.") if data else (False, "Aucune modification enregistrée.")
    except Exception as exc:
        return False, str(exc)


def get_journals(cabinet_id: Optional[str], limit: int = 200):
    if not cabinet_id:
        return []
    try:
        return (get_supabase().table("journals")
                .select("id,cabinet_id,code,name,journal_type,created_at")
                .eq("cabinet_id", cabinet_id)
                .order("code")
                .limit(_safe_limit(limit)).execute().data or [])
    except Exception:
        return []


def create_journal(cabinet_id: str, code: str, name: str, journal_type: Optional[str] = None):
    if not cabinet_id or not code.strip() or not name.strip():
        return False, "Le code et le nom du journal sont obligatoires."
    payload = {"cabinet_id": cabinet_id, "code": code.strip().upper(), "name": name.strip(), "journal_type": journal_type}
    try:
        data = get_supabase().table("journals").insert(payload).execute().data
        return (True, "Journal créé avec succès.") if data else (False, "La création du journal a échoué.")
    except Exception as exc:
        msg = str(exc)
        if "journals_unique_code" in msg or "duplicate key" in msg.lower():
            return False, "Ce code de journal existe déjà dans ce cabinet."
        return False, msg


def get_accounting_entries(cabinet_id: Optional[str], client_id: Optional[str] = None,
                           exercise_id: Optional[str] = None, status: Optional[str] = None, limit: int = 200):
    if not cabinet_id:
        return []
    try:
        query = (get_supabase().table("accounting_entries")
                 .select("id,cabinet_id,client_id,exercise_id,journal_id,document_id,entry_date,reference,label,status,created_by,validated_by,validated_at,created_at,updated_at,clients(name),exercises(year),journals(code,name)")
                 .eq("cabinet_id", cabinet_id)
                 .order("entry_date", desc=True)
                 .order("created_at", desc=True)
                 .limit(_safe_limit(limit)))
        if client_id:
            query = query.eq("client_id", client_id)
        if exercise_id:
            query = query.eq("exercise_id", exercise_id)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []
    except Exception:
        return []


def get_entry_lines(entry_id: Optional[str]):
    if not entry_id:
        return []
    try:
        return (get_supabase().table("accounting_entry_lines")
                .select("id,entry_id,account_id,account_number,account_name,label,debit,credit,created_at")
                .eq("entry_id", entry_id)
                .order("created_at")
                .execute().data or [])
    except Exception:
        return []


def create_accounting_entry(cabinet_id: str, client_id: str, exercise_id: Optional[str],
                            journal_id: Optional[str], document_id: Optional[str], entry_date,
                            reference: Optional[str], label: Optional[str], created_by: Optional[str],
                            lines: Iterable[Dict[str, Any]]):
    if not cabinet_id or not client_id or not entry_date:
        return False, None, "Cabinet, client et date sont obligatoires."
    normalized = []
    total_debit = 0.0
    total_credit = 0.0
    for line in lines:
        debit = round(float(line.get("debit") or 0), 2)
        credit = round(float(line.get("credit") or 0), 2)
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
            return False, None, "Chaque ligne doit avoir un débit ou un crédit, jamais les deux."
        if debit == 0 and credit == 0:
            continue
        normalized.append({
            "account_id": line.get("account_id"),
            "account_number": str(line.get("account_number") or "").strip(),
            "account_name": line.get("account_name"),
            "label": line.get("label"),
            "debit": debit,
            "credit": credit,
        })
        total_debit += debit
        total_credit += credit
    if not normalized:
        return False, None, "Ajoutez au moins une ligne comptable."
    if round(total_debit, 2) != round(total_credit, 2):
        return False, None, f"Écriture déséquilibrée : débit {total_debit:,.2f} ≠ crédit {total_credit:,.2f}."
    if total_debit <= 0:
        return False, None, "Le total de l'écriture doit être supérieur à zéro."

    payload = {
        "cabinet_id": cabinet_id,
        "client_id": client_id,
        "exercise_id": exercise_id,
        "journal_id": journal_id,
        "document_id": document_id,
        "entry_date": entry_date.isoformat() if hasattr(entry_date, "isoformat") else str(entry_date),
        "reference": reference.strip() if isinstance(reference, str) else reference,
        "label": label.strip() if isinstance(label, str) else label,
        "status": "brouillon",
        "created_by": created_by,
    }
    sb = get_supabase()
    try:
        created = sb.table("accounting_entries").insert(payload).execute().data
        if not created:
            return False, None, "La création de l'écriture a échoué."
        entry_id = created[0]["id"]
        line_payloads = [{"entry_id": entry_id, **line} for line in normalized]
        try:
            inserted_lines = sb.table("accounting_entry_lines").insert(line_payloads).execute().data
            if not inserted_lines or len(inserted_lines) != len(line_payloads):
                sb.table("accounting_entries").delete().eq("id", entry_id).eq("cabinet_id", cabinet_id).execute()
                return False, None, "Les lignes comptables n'ont pas pu être enregistrées."
        except Exception:
            sb.table("accounting_entries").delete().eq("id", entry_id).eq("cabinet_id", cabinet_id).execute()
            raise
        return True, entry_id, "Écriture créée en brouillon."
    except Exception as exc:
        return False, None, str(exc)


def submit_accounting_entry(entry_id: str, cabinet_id: str):
    if not entry_id or not cabinet_id:
        return False, "Écriture ou cabinet introuvable."
    try:
        data = (get_supabase().table("accounting_entries").update({"status": "a_valider"})
                .eq("id", entry_id).eq("cabinet_id", cabinet_id).eq("status", "brouillon")
                .execute().data)
        return (True, "Écriture envoyée pour validation.") if data else (False, "L'écriture n'est pas modifiable ou n'existe pas.")
    except Exception as exc:
        return False, str(exc)


def validate_accounting_entry(entry_id: str, cabinet_id: str, user_id: Optional[str] = None):
    if not entry_id or not cabinet_id:
        return False, "Écriture ou cabinet introuvable."
    try:
        result = get_supabase().rpc("validate_accounting_entry", {"target_entry": entry_id}).execute()
        valid = bool(result.data)
        if not valid:
            return False, "L'écriture est déséquilibrée ou ne peut pas être validée."
        payload = {"status": "validee"}
        if user_id:
            payload["validated_by"] = user_id
        payload["validated_at"] = datetime.now(timezone.utc).isoformat()
        data = (get_supabase().table("accounting_entries").update(payload)
                .eq("id", entry_id).eq("cabinet_id", cabinet_id)
                .in_("status", ["a_valider", "brouillon"]).execute().data)
        return (True, "Écriture validée.") if data else (False, "La validation n'a pas été enregistrée.")
    except Exception as exc:
        return False, str(exc)

# ============================================================
# FISCALITE — TVA / AIB / DECLARATIONS
# ============================================================

def get_tax_declarations(cabinet_id: Optional[str], client_id: Optional[str] = None,
                         status: Optional[str] = None, limit: int = 100):
    if not cabinet_id:
        return []
    try:
        query = (get_supabase().table("tax_declarations")
                 .select("id,cabinet_id,client_id,exercise_id,declaration_type,period_start,period_end,vat_collected,vat_deductible,vat_payable,aib_amount,status,due_date,notes,created_at,updated_at,clients(name),exercises(year)")
                 .eq("cabinet_id", cabinet_id)
                 .order("period_start", desc=True)
                 .limit(_safe_limit(limit)))
        if client_id:
            query = query.eq("client_id", client_id)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []
    except Exception:
        return []


def create_tax_declaration(cabinet_id: str, client_id: str, exercise_id: Optional[str],
                           declaration_type: str, period_start, period_end,
                           vat_collected: float = 0, vat_deductible: float = 0,
                           vat_payable: Optional[float] = None, aib_amount: float = 0,
                           due_date=None, notes: str = ""):
    if not cabinet_id or not client_id:
        return False, "Cabinet et client obligatoires."
    if period_end < period_start:
        return False, "La période de fin doit être postérieure ou égale à la période de début."
    payable = round(float(vat_collected or 0) - float(vat_deductible or 0), 2) if vat_payable is None else float(vat_payable)
    payload = {
        "cabinet_id": cabinet_id,
        "client_id": client_id,
        "exercise_id": exercise_id,
        "declaration_type": (declaration_type or "TVA").strip(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "vat_collected": float(vat_collected or 0),
        "vat_deductible": float(vat_deductible or 0),
        "vat_payable": payable,
        "aib_amount": float(aib_amount or 0),
        "status": "brouillon",
        "due_date": due_date.isoformat() if due_date else None,
        "notes": notes.strip() or None,
    }
    try:
        data = get_supabase().table("tax_declarations").insert(payload).execute().data
        return (True, "Déclaration créée avec succès.") if data else (False, "La déclaration n'a pas été créée.")
    except Exception as exc:
        return False, str(exc)


def update_tax_declaration(declaration_id: str, cabinet_id: str, values: Dict[str, Any]):
    allowed = {"vat_collected", "vat_deductible", "vat_payable", "aib_amount", "status", "due_date", "notes", "declaration_type", "period_start", "period_end", "exercise_id"}
    payload = {k: v for k, v in values.items() if k in allowed}
    if "period_start" in payload and hasattr(payload["period_start"], "isoformat"):
        payload["period_start"] = payload["period_start"].isoformat()
    if "period_end" in payload and hasattr(payload["period_end"], "isoformat"):
        payload["period_end"] = payload["period_end"].isoformat()
    if "due_date" in payload and payload["due_date"] is not None and hasattr(payload["due_date"], "isoformat"):
        payload["due_date"] = payload["due_date"].isoformat()
    if not declaration_id or not cabinet_id or not payload:
        return False, "Aucune modification à enregistrer."
    try:
        data = (get_supabase().table("tax_declarations").update(payload)
                .eq("id", declaration_id).eq("cabinet_id", cabinet_id).execute().data)
        return (True, "Déclaration mise à jour.") if data else (False, "Aucune modification n'a été enregistrée.")
    except Exception as exc:
        return False, str(exc)


def get_fiscal_document_totals(cabinet_id: Optional[str], client_id: Optional[str] = None,
                               start_date=None, end_date=None) -> Dict[str, float]:
    result = {"ht": 0.0, "vat": 0.0, "ttc": 0.0, "aib": 0.0, "documents": 0}
    if not cabinet_id:
        return result
    try:
        query = (get_supabase().table("documents")
                 .select("amount_ht,vat_amount,amount_ttc,aib_amount,invoice_date,status")
                 .eq("cabinet_id", cabinet_id)
                 .in_("status", ["analyse", "a_controler", "valide"]))
        if client_id:
            query = query.eq("client_id", client_id)
        if start_date:
            query = query.gte("invoice_date", start_date.isoformat())
        if end_date:
            query = query.lte("invoice_date", end_date.isoformat())
        rows = query.execute().data or []
        result["documents"] = len(rows)
        result["ht"] = round(sum(float(r.get("amount_ht") or 0) for r in rows), 2)
        result["vat"] = round(sum(float(r.get("vat_amount") or 0) for r in rows), 2)
        result["ttc"] = round(sum(float(r.get("amount_ttc") or 0) for r in rows), 2)
        result["aib"] = round(sum(float(r.get("aib_amount") or 0) for r in rows), 2)
    except Exception:
        pass
    return result



def create_accounting_control(cabinet_id: str, client_id: str, title: str,
                              description: str, severity: str = "warning",
                              document_id: Optional[str] = None):
    if not cabinet_id or not client_id or not title:
        return False, "Cabinet, client et titre sont obligatoires."
    if severity not in {"info", "warning", "critical"}:
        severity = "warning"
    payload = {
        "cabinet_id": cabinet_id,
        "client_id": client_id,
        "document_id": document_id,
        "title": title.strip(),
        "description": description.strip() if description else "",
        "severity": severity,
        "is_resolved": False,
    }
    try:
        data = get_supabase().table("accounting_controls").insert(payload).execute().data
        return (True, "Contrôle créé.") if data else (False, "Le contrôle n'a pas été créé.")
    except Exception as exc:
        return False, str(exc)


# --- Paramètres cabinet ---
from typing import Any, Dict, Optional


def get_cabinet(cabinet_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinets")
        .select("*")
        .eq("id", cabinet_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_cabinet(cabinet_id: str, payload: Dict[str, Any]) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinets")
        .update(payload)
        .eq("id", cabinet_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_cabinet_members(cabinet_id: str) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinet_members")
        .select("id,cabinet_id,user_id,role,created_at")
        .eq("cabinet_id", cabinet_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def update_member_role(member_id: str, role: str) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinet_members")
        .update({"role": role})
        .eq("id", member_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_cabinet_settings(cabinet_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinet_settings")
        .select("*")
        .eq("cabinet_id", cabinet_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_cabinet_settings(cabinet_id: str, payload: Dict[str, Any]) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("cabinet_settings")
        .upsert({"cabinet_id": cabinet_id, **payload}, on_conflict="cabinet_id")
        .execute()
    )
    return result.data[0] if result.data else None


def get_audit_logs(cabinet_id: str, limit: int = 100) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("audit_logs")
        .select("*")
        .eq("cabinet_id", cabinet_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []

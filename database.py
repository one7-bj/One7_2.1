from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client

from config import ADMIN_ROLES, WRITE_ROLES, get_supabase_key, get_supabase_url


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    return create_client(get_supabase_url(), get_supabase_key())


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


def sign_out() -> None:
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass


def _data(response) -> List[Dict[str, Any]]:
    return response.data or []


def get_user_cabinets() -> List[Dict[str, Any]]:
    user = get_current_user()
    if not user:
        return []
    try:
        response = (
            get_supabase()
            .table("cabinet_members")
            .select(
                "id, role, cabinet_id, cabinets(id, name, legal_name, ifu, rccm, address, phone, email, currency, logo_url)"
            )
            .eq("user_id", str(user.id))
            .order("created_at")
            .execute()
        )
        return _data(response)
    except Exception:
        return []


def get_user_cabinet() -> Optional[Dict[str, Any]]:
    memberships = get_user_cabinets()
    if not memberships:
        return None
    membership = memberships[0]
    return {
        "membership_id": membership["id"],
        "cabinet_id": membership["cabinet_id"],
        "role": membership["role"],
        "cabinet": membership.get("cabinets"),
    }


def create_cabinet(
    name: str,
    legal_name: Optional[str] = None,
    ifu: Optional[str] = None,
    rccm: Optional[str] = None,
) -> Tuple[bool, Optional[str], str]:
    try:
        response = get_supabase().rpc(
            "create_cabinet",
            {
                "cabinet_name": name.strip(),
                "cabinet_legal_name": legal_name.strip() if legal_name else None,
                "cabinet_ifu": ifu.strip() if ifu else None,
                "cabinet_rccm": rccm.strip() if rccm else None,
            },
        ).execute()
        if not response.data:
            return False, None, "La création du cabinet a échoué."
        return True, str(response.data), "Cabinet créé avec succès."
    except Exception as exc:
        return False, None, str(exc)


def get_cabinet_stats(cabinet_id: str) -> Dict[str, int]:
    stats = {"clients": 0, "documents": 0, "entries": 0, "anomalies": 0}
    try:
        sb = get_supabase()
        for key, table, column in [
            ("clients", "clients", "cabinet_id"),
            ("documents", "documents", "cabinet_id"),
            ("entries", "journal_entries", "cabinet_id"),
            ("anomalies", "documents", "cabinet_id"),
        ]:
            query = sb.table(table).select("id", count="exact").eq(column, cabinet_id)
            if key == "anomalies":
                query = query.eq("status", "anomaly")
            response = query.execute()
            stats[key] = int(response.count or 0)
    except Exception:
        pass
    return stats


def list_clients(cabinet_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
    try:
        query = (
            get_supabase()
            .table("clients")
            .select("*")
            .eq("cabinet_id", cabinet_id)
            .order("name")
        )
        if active_only:
            query = query.eq("is_active", True)
        return _data(query.execute())
    except Exception:
        return []


def create_client(cabinet_id: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        data = dict(payload)
        data["cabinet_id"] = cabinet_id
        response = get_supabase().table("clients").insert(data).execute()
        return bool(response.data), "Client créé avec succès." if response.data else "Création impossible."
    except Exception as exc:
        return False, str(exc)


def update_client(client_id: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        response = get_supabase().table("clients").update(payload).eq("id", client_id).execute()
        return bool(response.data), "Client mis à jour." if response.data else "Aucune modification."
    except Exception as exc:
        return False, str(exc)


def list_exercises(cabinet_id: str, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        query = (
            get_supabase()
            .table("exercises")
            .select("*")
            .eq("cabinet_id", cabinet_id)
            .order("start_date", desc=True)
        )
        if client_id:
            query = query.eq("client_id", client_id)
        return _data(query.execute())
    except Exception:
        return []


def list_documents(cabinet_id: str, client_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    try:
        query = (
            get_supabase()
            .table("documents")
            .select("*")
            .eq("cabinet_id", cabinet_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if client_id:
            query = query.eq("client_id", client_id)
        return _data(query.execute())
    except Exception:
        return []


def list_tax_declarations(cabinet_id: str, client_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    try:
        query = (
            get_supabase()
            .table("tax_declarations")
            .select("*")
            .eq("cabinet_id", cabinet_id)
            .order("period_start", desc=True)
            .limit(limit)
        )
        if client_id:
            query = query.eq("client_id", client_id)
        return _data(query.execute())
    except Exception:
        return []


def can_write(role: Optional[str]) -> bool:
    return role in WRITE_ROLES


def is_admin(role: Optional[str]) -> bool:
    return role in ADMIN_ROLES

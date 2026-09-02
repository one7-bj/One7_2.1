# ============================================================
# ONE7 V2.1
# database.py
# ============================================================

from functools import lru_cache

from supabase import create_client, Client

from config import get_supabase_url, get_supabase_key


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Crée une seule instance du client Supabase
    pour toute la session de l'application.
    """

    url = get_supabase_url()
    key = get_supabase_key()

    return create_client(url, key)


def get_current_user():
    """
    Retourne l'utilisateur actuellement connecté.
    """

    supabase = get_supabase()

    try:
        response = supabase.auth.get_user()

        if response is None:
            return None

        return response.user

    except Exception:
        return None


def get_current_session():
    """
    Retourne la session Supabase actuelle.
    """

    supabase = get_supabase()

    try:
        return supabase.auth.get_session()
    except Exception:
        return None


def sign_out():
    """
    Déconnecte l'utilisateur.
    """

    supabase = get_supabase()

    try:
        supabase.auth.sign_out()
    except Exception:
        pass

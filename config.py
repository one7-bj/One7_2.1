import streamlit as st

APP_NAME = "One7"
APP_VERSION = "2.1.1"
CURRENCY = "XOF"
CURRENCY_LABEL = "FCFA"


def get_supabase_url() -> str:
    try:
        return st.secrets["SUPABASE_URL"]
    except Exception as exc:
        raise RuntimeError(
            "SUPABASE_URL est introuvable dans .streamlit/secrets.toml"
        ) from exc


def get_supabase_key() -> str:
    try:
        return st.secrets["SUPABASE_KEY"]
    except Exception as exc:
        raise RuntimeError(
            "SUPABASE_KEY est introuvable dans .streamlit/secrets.toml"
        ) from exc


ROLES = {
    "admin": "Administrateur",
    "manager": "Responsable",
    "accountant": "Comptable",
    "assistant": "Assistant",
    "viewer": "Lecture seule",
}

WRITE_ROLES = {"admin", "manager", "accountant", "assistant"}
ADMIN_ROLES = {"admin", "manager"}

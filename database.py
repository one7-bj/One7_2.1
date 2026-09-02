# ============================================================
# ONE7 V2.1
# auth.py
# ============================================================

import streamlit as st

from database import get_supabase, get_current_user, sign_out


# ============================================================
# SESSION
# ============================================================

def initialize_session():
    """
    Initialise les variables Streamlit nécessaires.
    """

    defaults = {
        "authenticated": False,
        "user": None,
        "cabinet": None,
        "cabinet_role": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# CONNEXION
# ============================================================

def login(email: str, password: str):
    """
    Connecte un utilisateur avec email + mot de passe.
    """

    try:
        supabase = get_supabase()

        response = supabase.auth.sign_in_with_password(
            {
                "email": email.strip(),
                "password": password,
            }
        )

        if response.user is None:
            return False, "Connexion impossible."

        st.session_state.authenticated = True
        st.session_state.user = response.user

        load_user_context()

        return True, "Connexion réussie."

    except Exception as e:

        return False, f"Erreur de connexion Supabase : {e}"


# ============================================================
# INSCRIPTION
# ============================================================

def register(email: str, password: str):
    """
    Crée un compte utilisateur Supabase.
    """

    try:
        supabase = get_supabase()

        response = supabase.auth.sign_up(
            {
                "email": email.strip(),
                "password": password,
            }
        )

        if response.user is None:
            return False, "Impossible de créer le compte."

        return (
            True,
            "Compte créé. Vérifie ton adresse email si la confirmation est activée.",
        )

    except Exception as e:

        return False, str(e)


# ============================================================
# DECONNEXION
# ============================================================

def logout():
    """
    Déconnecte complètement l'utilisateur.
    """

    sign_out()

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.cabinet = None
    st.session_state.cabinet_role = None

    st.rerun()


# ============================================================
# UTILISATEUR COURANT
# ============================================================

def refresh_user():

    user = get_current_user()

    if user is None:

        st.session_state.authenticated = False
        st.session_state.user = None

        return None

    st.session_state.authenticated = True
    st.session_state.user = user

    return user


# ============================================================
# CABINET
# ============================================================

def get_user_cabinet():

    user = st.session_state.get("user")

    if user is None:
        return None

    supabase = get_supabase()

    try:

        response = (
            supabase
            .table("cabinet_members")
            .select(
                """
                id,
                role,
                cabinet_id,
                cabinets (
                    id,
                    name,
                    legal_name,
                    ifu,
                    rccm,
                    address,
                    phone,
                    email,
                    currency,
                    logo_url
                )
                """
            )
            .eq("user_id", str(user.id))
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        membership = response.data[0]

        cabinet = membership.get("cabinets")

        if not cabinet:
            return None

        return {
            "membership_id": membership["id"],
            "cabinet_id": membership["cabinet_id"],
            "role": membership["role"],
            "cabinet": cabinet,
        }

    except Exception:
        return None


# ============================================================
# CONTEXTE UTILISATEUR
# ============================================================

def load_user_context():

    context = get_user_cabinet()

    if context is None:

        st.session_state.cabinet = None
        st.session_state.cabinet_role = None

        return None

    st.session_state.cabinet = context["cabinet"]
    st.session_state.cabinet_role = context["role"]

    return context


# ============================================================
# CREATION DU CABINET
# ============================================================

def create_cabinet(
    name: str,
    legal_name: str = None,
    ifu: str = None,
    rccm: str = None,
):
    """
    Crée le cabinet de l'utilisateur actuellement connecté.

    La fonction SQL create_cabinet() installée dans Supabase
    crée également automatiquement le membre admin.
    """

    supabase = get_supabase()

    try:

        response = supabase.rpc(
            "create_cabinet",
            {
                "cabinet_name": name.strip(),
                "cabinet_legal_name": legal_name.strip()
                if legal_name
                else None,
                "cabinet_ifu": ifu.strip()
                if ifu
                else None,
                "cabinet_rccm": rccm.strip()
                if rccm
                else None,
            },
        ).execute()

        if not response.data:
            return False, None, "La création du cabinet a échoué."

        cabinet_id = response.data

        load_user_context()

        return True, cabinet_id, "Cabinet créé avec succès."

    except Exception as e:

        return False, None, str(e)


# ============================================================
# UTILISATEUR AUTHENTIFIE ?
# ============================================================

def is_authenticated():

    if st.session_state.get("authenticated"):
        return True

    user = refresh_user()

    return user is not None


# ============================================================
# CABINET CONFIGURE ?
# ============================================================

def has_cabinet():

    if st.session_state.get("cabinet"):
        return True

    context = load_user_context()

    return context is not None

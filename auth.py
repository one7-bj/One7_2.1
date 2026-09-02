import streamlit as st

from database import (
    create_cabinet as db_create_cabinet,
    get_current_user,
    get_supabase,
    get_user_cabinets,
    sign_out,
)


def initialize_session() -> None:
    defaults = {
        "authenticated": False,
        "user": None,
        "cabinet": None,
        "cabinet_role": None,
        "cabinet_membership_id": None,
        "selected_cabinet_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login(email: str, password: str):
    try:
        response = get_supabase().auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        if response.user is None:
            return False, "Connexion impossible."
        st.session_state.authenticated = True
        st.session_state.user = response.user
        load_user_context()
        return True, "Connexion réussie."
    except Exception as exc:
        return False, str(exc)


def register(email: str, password: str):
    try:
        response = get_supabase().auth.sign_up(
            {"email": email.strip(), "password": password}
        )
        if response.user is None:
            return False, "Impossible de créer le compte."
        return True, "Compte créé. Vérifie ton adresse email si la confirmation est activée."
    except Exception as exc:
        return False, str(exc)


def logout() -> None:
    sign_out()
    for key, value in {
        "authenticated": False,
        "user": None,
        "cabinet": None,
        "cabinet_role": None,
        "cabinet_membership_id": None,
        "selected_cabinet_id": None,
    }.items():
        st.session_state[key] = value
    st.rerun()


def refresh_user():
    user = get_current_user()
    if user is None:
        st.session_state.authenticated = False
        st.session_state.user = None
        return None
    st.session_state.authenticated = True
    st.session_state.user = user
    return user


def load_user_context(selected_id=None):
    memberships = get_user_cabinets()
    if not memberships:
        st.session_state.cabinet = None
        st.session_state.cabinet_role = None
        st.session_state.cabinet_membership_id = None
        return None

    wanted = selected_id or st.session_state.get("selected_cabinet_id")
    membership = next(
        (m for m in memberships if str(m["cabinet_id"]) == str(wanted)),
        memberships[0],
    )
    cabinet = membership.get("cabinets")
    st.session_state.selected_cabinet_id = membership["cabinet_id"]
    st.session_state.cabinet = cabinet
    st.session_state.cabinet_role = membership["role"]
    st.session_state.cabinet_membership_id = membership["id"]
    return {
        "membership_id": membership["id"],
        "cabinet_id": membership["cabinet_id"],
        "role": membership["role"],
        "cabinet": cabinet,
    }


def switch_cabinet(cabinet_id: str):
    return load_user_context(cabinet_id)


def get_cabinet_memberships():
    return get_user_cabinets()


def create_cabinet(name, legal_name=None, ifu=None, rccm=None):
    result = db_create_cabinet(name, legal_name, ifu, rccm)
    if result[0]:
        load_user_context(result[1])
    return result


def is_authenticated():
    if st.session_state.get("authenticated"):
        return True
    return refresh_user() is not None


def has_cabinet():
    if st.session_state.get("cabinet"):
        return True
    return load_user_context() is not None

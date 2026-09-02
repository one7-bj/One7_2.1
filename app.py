# ============================================================
# ONE7 V2.2
# app.py
# ============================================================

import streamlit as st

from config import APP_NAME, APP_VERSION
from auth import (
    initialize_session,
    is_authenticated,
    login,
    register,
    logout,
    has_cabinet,
    create_cabinet,
)
from database import get_dashboard_stats, get_recent_documents, get_open_controls


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title=f"{APP_NAME} — Cabinet comptable",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_session()


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
    .one7-title {
        font-size: 2.4rem;
        font-weight: 700;
        color: #173F5F;
        margin-bottom: 0;
    }
    .one7-subtitle {
        color: #64748B;
        font-size: 1rem;
        margin-top: 0;
    }
    .one7-card {
        background: white;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .one7-small {
        color: #64748B;
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PAGE DE CONNEXION
# ============================================================

def show_login():
    st.markdown('<div class="one7-title">One7</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="one7-subtitle">Plateforme de gestion comptable pour cabinets</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    tab_login, tab_register = st.tabs(["🔐 Connexion", "🆕 Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Adresse email", placeholder="exemple@email.com")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button(
                "Se connecter", type="primary", use_container_width=True
            )

            if submitted:
                if not email or not password:
                    st.error("Veuillez renseigner votre email et votre mot de passe.")
                else:
                    success, message = login(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    with tab_register:
        with st.form("register_form"):
            email = st.text_input(
                "Adresse email", key="register_email", placeholder="exemple@email.com"
            )
            password = st.text_input(
                "Mot de passe", type="password", key="register_password"
            )
            password_confirm = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button(
                "Créer mon compte", type="primary", use_container_width=True
            )

            if submitted:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs.")
                elif password != password_confirm:
                    st.error("Les deux mots de passe ne correspondent pas.")
                elif len(password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    success, message = register(email, password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


# ============================================================
# CREATION DU CABINET
# ============================================================

def show_create_cabinet():
    st.markdown('<div class="one7-title">Bienvenue sur One7</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="one7-subtitle">Commençons par créer votre cabinet.</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.info(
        "Votre compte est bien créé. Il faut maintenant créer votre cabinet comptable."
    )

    with st.form("create_cabinet_form"):
        name = st.text_input("Nom du cabinet *", placeholder="Cabinet ABC")
        legal_name = st.text_input(
            "Dénomination sociale", placeholder="ABC Expertise Comptable SARL"
        )
        col1, col2 = st.columns(2)
        with col1:
            ifu = st.text_input("IFU", placeholder="Numéro IFU")
        with col2:
            rccm = st.text_input("RCCM", placeholder="Numéro RCCM")

        submitted = st.form_submit_button(
            "Créer mon cabinet", type="primary", use_container_width=True
        )

        if submitted:
            if not name.strip():
                st.error("Le nom du cabinet est obligatoire.")
                return

            success, cabinet_id, message = create_cabinet(
                name=name,
                legal_name=legal_name,
                ifu=ifu,
                rccm=rccm,
            )

            if success:
                st.success("Cabinet créé avec succès.")
                st.rerun()
            else:
                st.error(message)


# ============================================================
# GARDES AUTHENTIFICATION / CABINET
# ============================================================

if not is_authenticated():
    show_login()
    st.caption(f"{APP_NAME} v{APP_VERSION}")
    st.stop()

if not has_cabinet():
    show_create_cabinet()
    st.stop()


# ============================================================
# CONTEXTE
# ============================================================

user = st.session_state.get("user")
cabinet = st.session_state.get("cabinet")
role = st.session_state.get("cabinet_role")
cabinet_id = cabinet.get("id") if cabinet else None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### 📊 One7")
    st.caption(f"Version {APP_VERSION}")
    st.divider()

    if cabinet:
        st.markdown(f"**🏢 {cabinet.get('name', 'Cabinet')}**")
        if role:
            st.caption(f"Rôle : {role.replace('_', ' ').title()}")

    if user:
        st.caption(user.email)

    st.divider()

    if st.button("🔄 Actualiser le tableau de bord", use_container_width=True):
        st.rerun()

    if st.button("🚪 Se déconnecter", use_container_width=True):
        logout()


# ============================================================
# DASHBOARD
# ============================================================

st.markdown('<div class="one7-title">Tableau de bord</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="one7-subtitle">Vue d’ensemble de l’activité de votre cabinet.</div>',
    unsafe_allow_html=True,
)
st.divider()

stats = get_dashboard_stats(cabinet_id)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("👥 Clients actifs", f"{stats['clients']:,}".replace(",", " "))
with col2:
    st.metric("📄 Documents", f"{stats['documents']:,}".replace(",", " "))
with col3:
    st.metric("📝 Écritures", f"{stats['ecritures']:,}".replace(",", " "))
with col4:
    st.metric("⚠️ Anomalies ouvertes", f"{stats['anomalies']:,}".replace(",", " "))

st.divider()

# Alertes opérationnelles
st.markdown("### 🎯 À traiter")
a1, a2, a3, a4 = st.columns(4)
with a1:
    st.metric("🔴 Documents à contrôler", stats["documents_a_controler"])
with a2:
    st.metric("🟠 Écritures à valider", stats["ecritures_a_valider"])
with a3:
    st.metric("🚨 Anomalies critiques", stats["anomalies_critiques"])
with a4:
    st.metric("📅 Déclarations à contrôler", stats["declarations_a_controler"])

st.divider()

left, right = st.columns([1.25, 1])

with left:
    st.markdown("### 📄 Documents récents")
    documents = get_recent_documents(cabinet_id, limit=5)

    if not documents:
        st.info("Aucun document récent pour le moment.")
    else:
        rows = []
        for doc in documents:
            client = doc.get("clients") or {}
            rows.append(
                {
                    "Document": doc.get("file_name") or "Sans nom",
                    "Client": client.get("name") if isinstance(client, dict) else "—",
                    "Type": doc.get("document_type") or "—",
                    "Statut": doc.get("status") or "—",
                    "TTC": doc.get("total_ttc") or 0,
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

with right:
    st.markdown("### ⚠️ Anomalies à surveiller")
    controls = get_open_controls(cabinet_id, limit=5)

    if not controls:
        st.success("Aucune anomalie ouverte actuellement.")
    else:
        for control in controls:
            severity = (control.get("severity") or "info").lower()
            icon = {
                "critical": "🚨",
                "error": "🔴",
                "warning": "🟠",
                "info": "🔵",
            }.get(severity, "🔵")
            client = control.get("clients") or {}
            client_name = client.get("name") if isinstance(client, dict) else None
            title = control.get("title") or "Contrôle"
            if client_name:
                title = f"{title} — {client_name}"
            st.warning(f"{icon} **{title}**")
            if control.get("description"):
                st.caption(control["description"])

st.divider()

st.caption(
    "Les indicateurs sont calculés à partir des données du cabinet connecté. "
    "Les restrictions d’accès restent appliquées par les politiques RLS Supabase."
)

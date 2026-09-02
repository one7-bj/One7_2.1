# ============================================================
# ONE7 V2.1
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


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title=f"{APP_NAME} — Cabinet comptable",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION
# ============================================================

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
        padding: 24px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PAGE DE CONNEXION
# ============================================================

def show_login():

    st.markdown(
        '<div class="one7-title">One7</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="one7-subtitle">'
        'Plateforme de gestion comptable pour cabinets'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    tab_login, tab_register = st.tabs(
        ["🔐 Connexion", "🆕 Créer un compte"]
    )

    # --------------------------------------------------------
    # CONNEXION
    # --------------------------------------------------------

    with tab_login:

        with st.form("login_form"):

            email = st.text_input(
                "Adresse email",
                placeholder="exemple@email.com",
            )

            password = st.text_input(
                "Mot de passe",
                type="password",
            )

            submitted = st.form_submit_button(
                "Se connecter",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not email or not password:

                    st.error(
                        "Veuillez renseigner votre email et votre mot de passe."
                    )

                else:

                    success, message = login(
                        email,
                        password,
                    )

                    if success:

                        st.success(message)

                        st.rerun()

                    else:

                        st.error(message)

    # --------------------------------------------------------
    # INSCRIPTION
    # --------------------------------------------------------

    with tab_register:

        with st.form("register_form"):

            email = st.text_input(
                "Adresse email",
                key="register_email",
                placeholder="exemple@email.com",
            )

            password = st.text_input(
                "Mot de passe",
                type="password",
                key="register_password",
            )

            password_confirm = st.text_input(
                "Confirmer le mot de passe",
                type="password",
            )

            submitted = st.form_submit_button(
                "Créer mon compte",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not email or not password:

                    st.error(
                        "Veuillez remplir tous les champs."
                    )

                elif password != password_confirm:

                    st.error(
                        "Les deux mots de passe ne correspondent pas."
                    )

                elif len(password) < 6:

                    st.error(
                        "Le mot de passe doit contenir au moins 6 caractères."
                    )

                else:

                    success, message = register(
                        email,
                        password,
                    )

                    if success:

                        st.success(message)

                    else:

                        st.error(message)


# ============================================================
# CREATION DU CABINET
# ============================================================

def show_create_cabinet():

    st.markdown(
        '<div class="one7-title">Bienvenue sur One7</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="one7-subtitle">'
        'Commençons par créer votre cabinet.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.info(
        "Votre compte est bien créé. "
        "Il faut maintenant créer votre cabinet comptable."
    )

    with st.form("create_cabinet_form"):

        name = st.text_input(
            "Nom du cabinet *",
            placeholder="Cabinet ABC",
        )

        legal_name = st.text_input(
            "Dénomination sociale",
            placeholder="ABC Expertise Comptable SARL",
        )

        col1, col2 = st.columns(2)

        with col1:

            ifu = st.text_input(
                "IFU",
                placeholder="Numéro IFU",
            )

        with col2:

            rccm = st.text_input(
                "RCCM",
                placeholder="Numéro RCCM",
            )

        submitted = st.form_submit_button(
            "Créer mon cabinet",
            type="primary",
            use_container_width=True,
        )

        if submitted:

            if not name.strip():

                st.error(
                    "Le nom du cabinet est obligatoire."
                )

                return

            success, cabinet_id, message = create_cabinet(
                name=name,
                legal_name=legal_name,
                ifu=ifu,
                rccm=rccm,
            )

            if success:

                st.success(
                    "Cabinet créé avec succès."
                )

                st.rerun()

            else:

                st.error(message)


# ============================================================
# UTILISATEUR CONNECTE
# ============================================================

if not is_authenticated():

    show_login()

    st.caption(
        f"{APP_NAME} v{APP_VERSION}"
    )

    st.stop()


# ============================================================
# CABINET
# ============================================================

if not has_cabinet():

    show_create_cabinet()

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

user = st.session_state.get("user")
cabinet = st.session_state.get("cabinet")
role = st.session_state.get("cabinet_role")


with st.sidebar:

    st.markdown(
        "### 📊 One7"
    )

    st.caption(
        f"Version {APP_VERSION}"
    )

    st.divider()

    if cabinet:

        st.markdown(
            f"**🏢 {cabinet.get('name', 'Cabinet')}**"
        )

        if role:

            st.caption(
                f"Rôle : {role.replace('_', ' ').title()}"
            )

    if user:

        st.caption(
            user.email
        )

    st.divider()

    if st.button(
        "🚪 Se déconnecter",
        use_container_width=True,
    ):

        logout()


# ============================================================
# DASHBOARD D'ACCUEIL
# ============================================================

st.markdown(
    '<div class="one7-title">Tableau de bord</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="one7-subtitle">'
    'Bienvenue dans votre espace de gestion comptable.'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "👥 Clients",
        "0",
    )

with col2:

    st.metric(
        "📄 Documents",
        "0",
    )

with col3:

    st.metric(
        "📝 Écritures",
        "0",
    )

with col4:

    st.metric(
        "⚠️ Anomalies",
        "0",
    )


st.divider()

st.info(
    "Le tableau de bord sera connecté aux modules Clients, "
    "Documents, Comptabilité et Fiscalité dans les prochaines étapes."
)

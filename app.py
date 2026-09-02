import streamlit as st

from auth import (
    create_cabinet,
    get_cabinet_memberships,
    has_cabinet,
    initialize_session,
    is_authenticated,
    load_user_context,
    login,
    logout,
    register,
    switch_cabinet,
)
from config import APP_NAME, APP_VERSION, ROLES
from database import get_cabinet_stats

st.set_page_config(
    page_title=f"{APP_NAME} — Cabinet comptable",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
initialize_session()

st.markdown(
    """
    <style>
    .one7-title {font-size:2.25rem;font-weight:750;margin-bottom:0;}
    .one7-subtitle {color:#64748B;font-size:1rem;margin-top:.15rem;}
    .one7-card {background:#fff;padding:1.1rem 1.2rem;border-radius:14px;border:1px solid #E2E8F0;}
    .one7-muted {color:#64748B;font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def show_login():
    st.markdown('<div class="one7-title">One7</div>', unsafe_allow_html=True)
    st.markdown('<div class="one7-subtitle">Plateforme de gestion comptable pour cabinets</div>', unsafe_allow_html=True)
    st.divider()
    tab_login, tab_register = st.tabs(["🔐 Connexion", "🆕 Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Adresse email", placeholder="exemple@email.com")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("Veuillez renseigner votre email et votre mot de passe.")
                else:
                    success, message = login(email, password)
                    if success:
                        st.rerun()
                    st.error(message) if not success else None

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Adresse email", key="register_email", placeholder="exemple@email.com")
            password = st.text_input("Mot de passe", key="register_password", type="password")
            confirmation = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button("Créer mon compte", type="primary", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs.")
                elif password != confirmation:
                    st.error("Les deux mots de passe ne correspondent pas.")
                elif len(password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    success, message = register(email, password)
                    (st.success if success else st.error)(message)


def show_create_cabinet():
    st.markdown('<div class="one7-title">Bienvenue sur One7</div>', unsafe_allow_html=True)
    st.markdown('<div class="one7-subtitle">Créons votre espace cabinet.</div>', unsafe_allow_html=True)
    st.divider()
    st.info("Votre compte est créé. Il faut maintenant créer ou rejoindre un cabinet.")
    with st.form("create_cabinet_form"):
        name = st.text_input("Nom du cabinet *", placeholder="Cabinet ABC")
        legal_name = st.text_input("Dénomination sociale", placeholder="ABC Expertise Comptable SARL")
        c1, c2 = st.columns(2)
        with c1:
            ifu = st.text_input("IFU")
        with c2:
            rccm = st.text_input("RCCM")
        submitted = st.form_submit_button("Créer mon cabinet", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Le nom du cabinet est obligatoire.")
                return
            success, _, message = create_cabinet(name, legal_name, ifu, rccm)
            if success:
                st.rerun()
            st.error(message)


def sidebar():
    user = st.session_state.get("user")
    cabinet = st.session_state.get("cabinet")
    memberships = get_cabinet_memberships()
    with st.sidebar:
        st.markdown("### 📊 One7")
        st.caption(f"Version {APP_VERSION}")
        st.divider()
        if memberships:
            labels = []
            ids = []
            for membership in memberships:
                cab = membership.get("cabinets") or {}
                labels.append(cab.get("name", "Cabinet"))
                ids.append(str(membership["cabinet_id"]))
            current = str(st.session_state.get("selected_cabinet_id") or ids[0])
            index = ids.index(current) if current in ids else 0
            choice = st.selectbox("🏢 Cabinet actif", labels, index=index)
            selected_id = ids[labels.index(choice)]
            if selected_id != current:
                switch_cabinet(selected_id)
                st.rerun()
        if cabinet:
            st.caption(f"Rôle : {ROLES.get(st.session_state.get('cabinet_role'), st.session_state.get('cabinet_role', ''))}")
        if user:
            st.caption(user.email)
        st.divider()
        st.markdown("**Navigation**")
        for label, target in [
            ("🏠 Tableau de bord", "app.py"),
            ("👥 Clients", "pages/1_👥_Clients.py"),
            ("📥 Documents", "pages/2_📥_Documents.py"),
            ("📒 Comptabilité", "pages/3_📒_Comptabilite.py"),
            ("📊 Fiscalité", "pages/4_📊_Fiscalite.py"),
            ("⚙️ Paramètres", "pages/5_⚙️_Parametres.py"),
        ]:
            try:
                st.page_link(target, label=label)
            except Exception:
                pass
        st.divider()
        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()


if not is_authenticated():
    show_login()
    st.caption(f"{APP_NAME} v{APP_VERSION}")
    st.stop()

if not has_cabinet():
    show_create_cabinet()
    st.stop()

sidebar()
cabinet = st.session_state.get("cabinet") or {}
st.markdown('<div class="one7-title">Tableau de bord</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="one7-subtitle">{cabinet.get("name", "Cabinet")} — vue de production comptable</div>',
    unsafe_allow_html=True,
)
st.divider()

stats = get_cabinet_stats(str(cabinet.get("id")))
c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Clients", stats["clients"])
c2.metric("📄 Documents", stats["documents"])
c3.metric("📝 Écritures", stats["entries"])
c4.metric("⚠️ Anomalies", stats["anomalies"])

st.divider()
left, right = st.columns([1.5, 1])
with left:
    st.subheader("🚀 Production")
    st.info("Utilisez le menu à gauche pour ouvrir les clients, importer les documents, contrôler les écritures et préparer la fiscalité.")
with right:
    st.subheader("📌 Prochaine étape")
    st.write("Sélectionnez un client dans **Clients** pour travailler sur son dossier.")

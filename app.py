import streamlit as st
from supabase import create_client, Client

# === 0. CONFIG + CONNEXION SUPABASE ===
st.set_page_config(page_title="One7 Pro - TVA & AIB Bénin", page_icon="🧾", layout="wide")
st.markdown("""<style>.stButton>button {background-color: #004AAD; color: white; border-radius: 8px;}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# === 1. GESTION LOGIN / SIGNUP ===
def auth_page():
    st.title("🧾 One7 Pro - Connexion")
    tab1, tab2 = st.tabs(["Se Connecter", "Créer un Compte"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e: st.error(f"Erreur: {e}")

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Mot de passe", type="password", key="signup_pass")
        nom_cabinet = st.text_input("Nom du Cabinet")
        if st.button("Créer le compte"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                supabase.table('profiles').insert({"id": res.user.id, "email": email, "nom_cabinet": nom_cabinet}).execute()
                st.success("Compte créé! Connecte-toi maintenant.")
            except Exception as e: st.error(f"Erreur: {e}")

if 'user' not in st.session_state:
    try: st.session_state.user = supabase.auth.get_user().user
    except: st.session_state.user = None

if not st.session_state.user:
    auth_page()
    st.stop()

# === SI CONNECTE ===
user_id = st.session_state.user.id
st.sidebar.success(f"Connecté: {st.session_state.user.email}")
if st.sidebar.button("Se déconnecter"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

st.title("🧾 One7 Pro - Déclaration TVA & AIB Bénin")
st.caption("Version Cloud Supabase - Multi-utilisateurs")

# MENU MULTI-PAGES
pg = st.navigation([
    st.Page("pages/1_📥_Import.py", title="Import", icon="📥"),
    st.Page("pages/2_📝_Imputation.py", title="Imputation", icon="📝"),
    st.Page("pages/3_📊_Declaration.py", title="Déclaration TVA", icon="📊"),
    st.Page("pages/4_⚙️_Parametres.py", title="Paramètres", icon="⚙️"),
])
pg.run()

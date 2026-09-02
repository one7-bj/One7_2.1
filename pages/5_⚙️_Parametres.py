import streamlit as st

from auth import has_cabinet, is_authenticated
from config import APP_VERSION, ROLES

st.set_page_config(page_title="One7 — Paramètres", page_icon="⚙️", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet actif.")
    st.stop()

cabinet = st.session_state.cabinet
role = st.session_state.cabinet_role

st.title("⚙️ Paramètres")
st.caption(f"One7 {APP_VERSION}")

st.subheader("🏢 Cabinet actif")
st.write(f"**Nom :** {cabinet.get('name') or '—'}")
st.write(f"**Dénomination :** {cabinet.get('legal_name') or '—'}")
st.write(f"**IFU :** {cabinet.get('ifu') or '—'}")
st.write(f"**RCCM :** {cabinet.get('rccm') or '—'}")
st.write(f"**Devise :** {cabinet.get('currency') or 'XOF'}")
st.write(f"**Votre rôle :** {ROLES.get(role, role)}")

st.divider()
st.subheader("🤖 Intelligence One7")
st.checkbox("Activer les suggestions d'imputation", value=True)
st.checkbox("Activer les contrôles automatiques des factures", value=True)
st.checkbox("Exiger une validation humaine avant comptabilisation", value=True)

st.divider()
st.info("Les paramètres avancés, utilisateurs, plan comptable et règles fiscales seront ajoutés sur la couche cabinet.")

import streamlit as st

from auth import has_cabinet, is_authenticated
from database import create_client, list_clients

st.set_page_config(page_title="One7 — Clients", page_icon="👥", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet actif.")
    st.stop()

cabinet = st.session_state.cabinet
cabinet_id = str(cabinet["id"])

st.title("👥 Clients")
st.caption("Gestion des dossiers clients du cabinet")

with st.expander("➕ Ajouter un client", expanded=False):
    with st.form("new_client"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom / raison sociale *")
            ifu = st.text_input("IFU")
            rccm = st.text_input("RCCM")
        with c2:
            legal_form = st.text_input("Forme juridique")
            regime = st.text_input("Régime fiscal")
            activity = st.text_input("Activité")
        address = st.text_input("Adresse")
        phone = st.text_input("Téléphone")
        email = st.text_input("Email")
        submitted = st.form_submit_button("Créer le client", type="primary")
        if submitted:
            if not name.strip():
                st.error("Le nom du client est obligatoire.")
            else:
                ok, message = create_client(
                    cabinet_id,
                    {
                        "name": name.strip(),
                        "ifu": ifu.strip() or None,
                        "rccm": rccm.strip() or None,
                        "legal_form": legal_form.strip() or None,
                        "tax_regime": regime.strip() or None,
                        "activity": activity.strip() or None,
                        "address": address.strip() or None,
                        "phone": phone.strip() or None,
                        "email": email.strip() or None,
                    },
                )
                (st.success if ok else st.error)(message)
                if ok:
                    st.rerun()

clients = list_clients(cabinet_id)
search = st.text_input("🔎 Rechercher un client", placeholder="Nom, IFU ou RCCM")
if search:
    term = search.lower()
    clients = [
        c for c in clients
        if term in str(c.get("name", "")).lower()
        or term in str(c.get("ifu", "")).lower()
        or term in str(c.get("rccm", "")).lower()
    ]

st.write(f"**{len(clients)}** client(s)")
if not clients:
    st.info("Aucun client trouvé. Créez votre premier dossier.")
else:
    for client in clients:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"### {client.get('name', 'Client')}")
            c1.caption(f"IFU : {client.get('ifu') or '—'}  |  RCCM : {client.get('rccm') or '—'}")
            c2.write(f"**Régime**\n\n{client.get('tax_regime') or '—'}")
            c3.write(f"**Statut**\n\n{'Actif' if client.get('is_active', True) else 'Inactif'}")

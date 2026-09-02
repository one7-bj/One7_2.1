import streamlit as st

from auth import has_cabinet, is_authenticated
from database import list_clients, list_documents

st.set_page_config(page_title="One7 — Documents", page_icon="📥", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet actif.")
    st.stop()

cabinet_id = str(st.session_state.cabinet["id"])
clients = list_clients(cabinet_id, active_only=True)
client_options = {"Tous les clients": None}
client_options.update({c["name"]: c["id"] for c in clients})

st.title("📥 Documents")
st.caption("Centralisation des pièces comptables et suivi du traitement")

selected_name = st.selectbox("Client", list(client_options.keys()))
client_id = client_options[selected_name]

uploaded = st.file_uploader("Importer une facture ou une pièce", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
if uploaded:
    st.info(f"{len(uploaded)} fichier(s) reçu(s). Le pipeline OCR/IA pourra les enregistrer après validation du client sélectionné.")
    for file in uploaded:
        st.write(f"📄 {file.name} — {file.size:,} octets")

st.divider()
documents = list_documents(cabinet_id, client_id, limit=200)
st.subheader(f"📚 Documents récents ({len(documents)})")
if not documents:
    st.info("Aucun document enregistré pour cette sélection.")
else:
    for doc in documents:
        status = doc.get("status", "pending")
        icon = {"validated": "🟢", "anomaly": "🔴", "processed": "🟠"}.get(status, "⚪")
        st.write(f"{icon} **{doc.get('file_name', 'Document')}** — {status} — {doc.get('document_date') or 'date inconnue'}")

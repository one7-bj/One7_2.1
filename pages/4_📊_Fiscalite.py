import streamlit as st

from auth import has_cabinet, is_authenticated
from database import list_clients, list_tax_declarations

st.set_page_config(page_title="One7 — Fiscalité", page_icon="📊", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet actif.")
    st.stop()

cabinet_id = str(st.session_state.cabinet["id"])
clients = list_clients(cabinet_id, active_only=True)
options = {"Tous les clients": None}
options.update({c["name"]: c["id"] for c in clients})

st.title("📊 Fiscalité")
st.caption("Préparation et suivi des déclarations fiscales")
selected = st.selectbox("Client", list(options.keys()))
client_id = options[selected]

declarations = list_tax_declarations(cabinet_id, client_id)

c1, c2, c3 = st.columns(3)
ready = sum(1 for d in declarations if d.get("status") == "ready")
review = sum(1 for d in declarations if d.get("status") in {"draft", "review"})
anomaly = sum(1 for d in declarations if d.get("status") == "anomaly")
c1.metric("🟢 Prêtes", ready)
c2.metric("🟠 À contrôler", review)
c3.metric("🔴 Anomalies", anomaly)

st.divider()
st.subheader("🧾 Déclarations")
if not declarations:
    st.info("Aucune déclaration enregistrée.")
else:
    for declaration in declarations:
        st.write(f"**{declaration.get('tax_type', 'TVA')}** — {declaration.get('period_start')} → {declaration.get('period_end')} — **{declaration.get('status', 'draft')}**")

st.divider()
st.subheader("🤖 Assistant fiscal")
st.info("Le moteur fiscal doit être relié à une base documentaire officielle avant de produire des réponses réglementaires. L'IA ne doit pas être utilisée seule comme source juridique.")

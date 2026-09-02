import streamlit as st

from auth import has_cabinet, is_authenticated
from database import list_clients, get_supabase

st.set_page_config(page_title="One7 — Comptabilité", page_icon="📒", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet actif.")
    st.stop()

cabinet_id = str(st.session_state.cabinet["id"])
clients = list_clients(cabinet_id, active_only=True)
options = {"Tous les clients": None}
options.update({c["name"]: c["id"] for c in clients})

st.title("📒 Comptabilité")
st.caption("Journaux, écritures et contrôle de l'équilibre comptable")
selected = st.selectbox("Client", list(options.keys()))
client_id = options[selected]

try:
    query = get_supabase().table("journal_entries").select("*, journal_lines(*)").eq("cabinet_id", cabinet_id).order("entry_date", desc=True).limit(100)
    if client_id:
        query = query.eq("client_id", client_id)
    entries = query.execute().data or []
except Exception:
    entries = []

if not entries:
    st.info("Aucune écriture enregistrée pour cette sélection.")
else:
    for entry in entries:
        lines = entry.get("journal_lines") or []
        debit = sum(float(x.get("debit") or 0) for x in lines)
        credit = sum(float(x.get("credit") or 0) for x in lines)
        balanced = abs(debit - credit) < 0.01
        icon = "🟢" if balanced else "🔴"
        with st.expander(f"{icon} {entry.get('entry_number') or entry.get('id')} — {entry.get('entry_date')} — {entry.get('label') or 'Écriture'}"):
            st.write(f"Débit : **{debit:,.0f} FCFA** | Crédit : **{credit:,.0f} FCFA**")
            if not balanced:
                st.error(f"Écriture déséquilibrée : écart de {debit-credit:,.0f} FCFA")
            for line in lines:
                st.write(f"`{line.get('account_number','—')}` {line.get('account_label','')} — Débit {float(line.get('debit') or 0):,.0f} / Crédit {float(line.get('credit') or 0):,.0f}")

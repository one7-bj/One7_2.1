# ============================================================
# ONE7 V2.2 — COMPTABILITE
# ============================================================

from datetime import date
import streamlit as st

from auth import initialize_session, is_authenticated, has_cabinet, logout
from database import (
    get_clients,
    get_client_exercises,
    get_chart_of_accounts,
    create_chart_account,
    update_chart_account,
    get_journals,
    create_journal,
    get_accounting_entries,
    get_entry_lines,
    create_accounting_entry,
    submit_accounting_entry,
    validate_accounting_entry,
)

st.set_page_config(page_title="One7 — Comptabilité", page_icon="📒", layout="wide")
initialize_session()

if not is_authenticated():
    st.warning("Veuillez vous connecter depuis la page d'accueil.")
    st.stop()
if not has_cabinet():
    st.warning("Veuillez d'abord créer votre cabinet.")
    st.stop()

cabinet = st.session_state.get("cabinet") or {}
cabinet_id = cabinet.get("id")
role = st.session_state.get("cabinet_role") or "lecture"
user = st.session_state.get("user")
WRITE_ROLES = {"admin", "expert_comptable", "comptable", "assistant"}
ADMIN_ROLES = {"admin", "expert_comptable"}
can_write = role in WRITE_ROLES
can_admin = role in ADMIN_ROLES

with st.sidebar:
    st.markdown("### 📊 One7")
    st.caption(f"🏢 {cabinet.get('name', 'Cabinet')}")
    st.caption(f"Rôle : {role.replace('_', ' ').title()}")
    st.divider()
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()
    if st.button("🚪 Se déconnecter", use_container_width=True):
        logout()

st.markdown("# 📒 Comptabilité")
st.caption("Plan comptable, journaux et écritures comptables du cabinet.")
st.divider()

clients = get_clients(cabinet_id, status="actif", limit=500)
client_options = {c.get("name", "Client"): c.get("id") for c in clients}

# ------------------------------------------------------------
# PLAN COMPTABLE / JOURNAUX
# ------------------------------------------------------------
tab_entries, tab_accounts, tab_journals = st.tabs(["🧾 Écritures", "📚 Plan comptable", "📓 Journaux"])

with tab_accounts:
    st.subheader("Plan comptable du cabinet")
    accounts = get_chart_of_accounts(cabinet_id, active_only=False)
    if can_write:
        with st.expander("➕ Ajouter un compte", expanded=False):
            with st.form("new_account"):
                c1, c2, c3 = st.columns([1.2, 2.5, 1])
                number = c1.text_input("Numéro *", placeholder="601100")
                name = c2.text_input("Intitulé *", placeholder="Achats de marchandises")
                acc_class = c3.number_input("Classe", min_value=1, max_value=9, value=6, step=1)
                acc_type = st.text_input("Type", placeholder="charge")
                if st.form_submit_button("Créer le compte", type="primary"):
                    ok, msg = create_chart_account(cabinet_id, number, name, int(acc_class), acc_type)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()
    else:
        st.info("Votre rôle est en lecture seule.")

    if accounts:
        rows = [{"N°": a.get("account_number"), "Intitulé": a.get("account_name"), "Classe": a.get("account_class"), "Type": a.get("account_type") or "", "Actif": "Oui" if a.get("is_active") else "Non"} for a in accounts]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if can_admin:
            st.caption("La modification détaillée des comptes sera enrichie dans une prochaine étape.")
    else:
        st.info("Aucun compte n'est encore configuré pour ce cabinet.")

with tab_journals:
    st.subheader("Journaux comptables")
    journals = get_journals(cabinet_id)
    if can_write:
        with st.expander("➕ Ajouter un journal", expanded=False):
            with st.form("new_journal"):
                c1, c2, c3 = st.columns([1, 2, 1.5])
                code = c1.text_input("Code *", placeholder="AC")
                name = c2.text_input("Nom *", placeholder="Achats")
                jtype = c3.selectbox("Type", ["Achats", "Ventes", "Banque", "Caisse", "Opérations diverses", "Autre"])
                if st.form_submit_button("Créer le journal", type="primary"):
                    ok, msg = create_journal(cabinet_id, code, name, jtype)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()
    if journals:
        st.dataframe([{"Code": j.get("code"), "Nom": j.get("name"), "Type": j.get("journal_type") or ""} for j in journals], use_container_width=True, hide_index=True)
    else:
        st.info("Aucun journal n'est encore configuré pour ce cabinet.")

with tab_entries:
    st.subheader("Écritures comptables")
    if not client_options:
        st.info("Créez d'abord un client actif dans le module Clients.")
        st.stop()

    f1, f2, f3 = st.columns(3)
    filter_client_name = f1.selectbox("Client", ["Tous les clients"] + list(client_options.keys()), key="entry_filter_client")
    filter_client_id = None if filter_client_name == "Tous les clients" else client_options[filter_client_name]
    filter_status = f2.selectbox("Statut", ["Tous", "brouillon", "a_valider", "validee", "rejetee"], key="entry_filter_status")
    filter_status_value = None if filter_status == "Tous" else filter_status
    filter_exercise = None
    if filter_client_id:
        exercises = get_client_exercises(filter_client_id)
        ex_labels = ["Tous les exercices"] + [f"{e.get('year')} — {e.get('status')}" for e in exercises]
        selected_ex = f3.selectbox("Exercice", ex_labels, key="entry_filter_exercise")
        if selected_ex != "Tous les exercices":
            idx = ex_labels.index(selected_ex) - 1
            filter_exercise = exercises[idx].get("id")
    else:
        f3.info("Choisissez un client pour filtrer par exercice.")

    entries = get_accounting_entries(cabinet_id, filter_client_id, filter_exercise, filter_status_value)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Écritures", len(entries))
    m2.metric("Brouillons", sum(e.get("status") == "brouillon" for e in entries))
    m3.metric("À valider", sum(e.get("status") == "a_valider" for e in entries))
    m4.metric("Validées", sum(e.get("status") == "validee" for e in entries))

    if can_write:
        with st.expander("➕ Nouvelle écriture", expanded=False):
            client_name = st.selectbox("Client *", list(client_options.keys()), key="new_entry_client")
            client_id = client_options[client_name]
            exercises = get_client_exercises(client_id)
            open_exercises = [e for e in exercises if e.get("status") == "ouvert"]
            if not open_exercises:
                st.warning("Ce client ne possède aucun exercice ouvert.")
            else:
                exercise_labels = [f"{e.get('year')} ({e.get('start_date')} → {e.get('end_date')})" for e in open_exercises]
                selected_ex_idx = st.selectbox("Exercice *", range(len(open_exercises)), format_func=lambda i: exercise_labels[i], key="new_entry_exercise")
                selected_exercise = open_exercises[selected_ex_idx]
                journals = get_journals(cabinet_id)
                journal_map = {f"{j.get('code')} — {j.get('name')}": j.get('id') for j in journals}
                journal_label = st.selectbox("Journal", ["Aucun"] + list(journal_map.keys()), key="new_entry_journal")
                journal_id = journal_map.get(journal_label)
                entry_date = st.date_input("Date", value=date.today(), key="new_entry_date")
                reference = st.text_input("Référence", placeholder="FAC-2026-001", key="new_entry_ref")
                label = st.text_input("Libellé", placeholder="Achat de marchandises", key="new_entry_label")

                accounts = get_chart_of_accounts(cabinet_id, active_only=True)
                account_map = {f"{a.get('account_number')} — {a.get('account_name')}": a for a in accounts}
                if not account_map:
                    st.warning("Configurez d'abord le plan comptable.")
                else:
                    if "one7_entry_lines" not in st.session_state:
                        st.session_state.one7_entry_lines = [{"account": list(account_map.keys())[0], "label": "", "debit": 0.0, "credit": 0.0}]
                    lines = st.session_state.one7_entry_lines
                    edited = st.data_editor(
                        lines,
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "account": st.column_config.SelectboxColumn("Compte", options=list(account_map.keys()), required=True),
                            "label": st.column_config.TextColumn("Libellé"),
                            "debit": st.column_config.NumberColumn("Débit", min_value=0, format="%.2f"),
                            "credit": st.column_config.NumberColumn("Crédit", min_value=0, format="%.2f"),
                        },
                        key="entry_lines_editor",
                    )
                    st.session_state.one7_entry_lines = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
                    total_d = sum(float(x.get("debit") or 0) for x in st.session_state.one7_entry_lines)
                    total_c = sum(float(x.get("credit") or 0) for x in st.session_state.one7_entry_lines)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total débit", f"{total_d:,.2f} FCFA")
                    c2.metric("Total crédit", f"{total_c:,.2f} FCFA")
                    c3.metric("Écart", f"{(total_d-total_c):,.2f} FCFA")
                    if st.button("💾 Enregistrer l'écriture", type="primary", key="save_entry"):
                        normalized = []
                        for row in st.session_state.one7_entry_lines:
                            acc = account_map.get(row.get("account"))
                            if not acc:
                                continue
                            normalized.append({"account_id": acc.get("id"), "account_number": acc.get("account_number"), "account_name": acc.get("account_name"), "label": row.get("label"), "debit": row.get("debit"), "credit": row.get("credit")})
                        ok, entry_id, msg = create_accounting_entry(cabinet_id, client_id, selected_exercise.get("id"), journal_id, None, entry_date, reference, label, getattr(user, "id", None), normalized)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.session_state.pop("one7_entry_lines", None)
                            st.rerun()

    st.divider()
    if entries:
        for entry in entries:
            client = entry.get("clients") or {}
            journal = entry.get("journals") or {}
            title = f"{entry.get('entry_date')} — {entry.get('label') or 'Sans libellé'}"
            with st.expander(f"{title}  ·  {entry.get('status')}  ·  {client.get('name', '')}"):
                st.write(f"**Référence :** {entry.get('reference') or '—'}  |  **Journal :** {journal.get('code') or '—'}")
                lines = get_entry_lines(entry.get("id"))
                st.dataframe([{"Compte": l.get("account_number"), "Libellé": l.get("label") or l.get("account_name") or "", "Débit": float(l.get("debit") or 0), "Crédit": float(l.get("credit") or 0)} for l in lines], use_container_width=True, hide_index=True)
                total_d = sum(float(l.get("debit") or 0) for l in lines)
                total_c = sum(float(l.get("credit") or 0) for l in lines)
                st.caption(f"Débit : {total_d:,.2f} FCFA · Crédit : {total_c:,.2f} FCFA · Écart : {(total_d-total_c):,.2f} FCFA")
                b1, b2 = st.columns(2)
                if can_write and entry.get("status") == "brouillon" and b1.button("📤 Soumettre", key=f"submit_{entry['id']}"):
                    ok, msg = submit_accounting_entry(entry["id"], cabinet_id)
                    (st.success if ok else st.error)(msg)
                    if ok: st.rerun()
                if can_admin and entry.get("status") == "a_valider" and b2.button("✅ Valider", key=f"validate_{entry['id']}"):
                    ok, msg = validate_accounting_entry(entry["id"], cabinet_id, getattr(user, "id", None))
                    (st.success if ok else st.error)(msg)
                    if ok: st.rerun()
    else:
        st.info("Aucune écriture ne correspond aux filtres.")

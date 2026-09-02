import streamlit as st
from datetime import date, timedelta

from auth import is_authenticated, has_cabinet
from database import (
    get_clients, get_client_exercises, get_tax_declarations,
    create_tax_declaration, update_tax_declaration,
    get_fiscal_document_totals,
)

st.set_page_config(page_title="One7 — Fiscalité", page_icon="📊", layout="wide")

if not is_authenticated() or not has_cabinet():
    st.warning("Veuillez vous connecter et disposer d'un cabinet.")
    st.stop()

cabinet = st.session_state.get("cabinet") or {}
cabinet_id = cabinet.get("id")
role = st.session_state.get("cabinet_role") or "lecture"
can_write = role in {"admin", "expert_comptable", "comptable", "assistant"}
can_validate = role in {"admin", "expert_comptable"}

st.title("📊 Fiscalité")
st.caption("TVA, AIB, déclarations et suivi des échéances fiscales")

clients = get_clients(cabinet_id, status="actif")
client_map = {c.get("name"): c.get("id") for c in clients}

if not client_map:
    st.info("Créez d'abord un client actif dans le module Clients.")
    st.stop()

# Vue synthèse
all_declarations = get_tax_declarations(cabinet_id, limit=200)
today = date.today()
late = [d for d in all_declarations if d.get("status") in {"brouillon", "a_controler"} and d.get("due_date") and d.get("due_date") < today.isoformat()]
to_check = [d for d in all_declarations if d.get("status") == "a_controler"]
deposited = [d for d in all_declarations if d.get("status") == "deposee"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Déclarations", len(all_declarations))
m2.metric("À contrôler", len(to_check))
m3.metric("En retard", len(late))
m4.metric("Déposées", len(deposited))

st.divider()

tab_dashboard, tab_declarations, tab_calcul = st.tabs(["📌 Synthèse", "🧾 Déclarations", "🧮 Calcul fiscal"])

with tab_dashboard:
    st.subheader("Suivi des obligations")
    if late:
        st.error(f"⚠️ {len(late)} déclaration(s) ont dépassé leur échéance.")
    elif to_check:
        st.warning(f"🔎 {len(to_check)} déclaration(s) attendent un contrôle.")
    else:
        st.success("Aucune déclaration en retard ou en attente de contrôle.")

    if all_declarations:
        rows = []
        for d in all_declarations[:30]:
            client = d.get("clients") or {}
            rows.append({
                "Client": client.get("name", ""),
                "Type": d.get("declaration_type"),
                "Période": f"{d.get('period_start')} → {d.get('period_end')}",
                "TVA à payer": float(d.get("vat_payable") or 0),
                "AIB": float(d.get("aib_amount") or 0),
                "Échéance": d.get("due_date") or "—",
                "Statut": d.get("status"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune déclaration enregistrée.")

with tab_declarations:
    st.subheader("Déclarations fiscales")
    c1, c2 = st.columns(2)
    selected_client_name = c1.selectbox("Client", list(client_map.keys()), key="fiscal_client")
    selected_client_id = client_map[selected_client_name]
    status_filter = c2.selectbox("Statut", ["Tous", "brouillon", "a_controler", "validee", "deposee", "archivee"])
    declarations = get_tax_declarations(cabinet_id, selected_client_id, None if status_filter == "Tous" else status_filter)

    if can_write:
        with st.expander("➕ Nouvelle déclaration", expanded=False):
            exercises = get_client_exercises(selected_client_id)
            exercise_options = {f"{e.get('year')} — {e.get('status')}": e.get("id") for e in exercises}
            ex_label = st.selectbox("Exercice", ["Aucun"] + list(exercise_options.keys()))
            exercise_id = exercise_options.get(ex_label)
            dtype = st.selectbox("Type de déclaration", ["TVA", "AIB", "TVA + AIB", "Autre"])
            p1, p2 = st.columns(2)
            period_start = p1.date_input("Début de période", date(today.year, today.month, 1))
            period_end = p2.date_input("Fin de période", today)
            v1, v2, v3 = st.columns(3)
            vat_collected = v1.number_input("TVA collectée", min_value=0.0, step=100.0)
            vat_deductible = v2.number_input("TVA déductible", min_value=0.0, step=100.0)
            aib_amount = v3.number_input("AIB", min_value=0.0, step=100.0)
            payable = round(vat_collected - vat_deductible, 2)
            st.metric("TVA à payer", f"{payable:,.2f} FCFA")
            due_date = st.date_input("Date d'échéance", today + timedelta(days=15))
            notes = st.text_area("Notes")
            if st.form_submit_button("💾 Créer la déclaration", type="primary"):
                ok, msg = create_tax_declaration(cabinet_id, selected_client_id, exercise_id, dtype, period_start, period_end, vat_collected, vat_deductible, payable, aib_amount, due_date, notes)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

    if declarations:
        for d in declarations:
            client = d.get("clients") or {}
            title = f"{d.get('declaration_type')} — {d.get('period_start')} → {d.get('period_end')}"
            with st.expander(f"{title} · {d.get('status')}"):
                st.write(f"**Client :** {client.get('name', selected_client_name)}")
                a,b,c,dcol = st.columns(4)
                a.metric("TVA collectée", f"{float(d.get('vat_collected') or 0):,.2f}")
                b.metric("TVA déductible", f"{float(d.get('vat_deductible') or 0):,.2f}")
                c.metric("TVA à payer", f"{float(d.get('vat_payable') or 0):,.2f}")
                dcol.metric("AIB", f"{float(d.get('aib_amount') or 0):,.2f}")
                st.caption(f"Échéance : {d.get('due_date') or '—'}")
                if can_validate and d.get("status") == "brouillon":
                    if st.button("🔎 Passer à contrôler", key=f"control_{d['id']}"):
                        ok, msg = update_tax_declaration(d["id"], cabinet_id, {"status": "a_controler"})
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()
                if can_validate and d.get("status") == "a_controler":
                    if st.button("✅ Valider", key=f"validate_tax_{d['id']}"):
                        ok, msg = update_tax_declaration(d["id"], cabinet_id, {"status": "validee"})
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()
                if can_validate and d.get("status") == "validee":
                    if st.button("📤 Marquer déposée", key=f"deposit_{d['id']}"):
                        ok, msg = update_tax_declaration(d["id"], cabinet_id, {"status": "deposee"})
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()
    else:
        st.info("Aucune déclaration pour ce client avec ce filtre.")

with tab_calcul:
    st.subheader("Calcul indicatif à partir des documents")
    st.caption("Les montants ci-dessous sont une synthèse des documents déjà analysés, à contrôler avant toute déclaration.")
    calc_client = st.selectbox("Client", list(client_map.keys()), key="calc_client")
    calc_id = client_map[calc_client]
    start = st.date_input("Du", date(today.year, 1, 1), key="calc_start")
    end = st.date_input("Au", today, key="calc_end")
    totals = get_fiscal_document_totals(cabinet_id, calc_id, start, end)
    x1,x2,x3,x4 = st.columns(4)
    x1.metric("Documents", totals["documents"])
    x2.metric("Total HT", f"{totals['ht']:,.2f} FCFA")
    x3.metric("TVA", f"{totals['vat']:,.2f} FCFA")
    x4.metric("AIB", f"{totals['aib']:,.2f} FCFA")
    st.info("Ce calcul est une base de contrôle interne. Les règles fiscales définitives (taux, régimes, échéances et traitement AIB/TVA) seront paramétrées avant mise en production.")

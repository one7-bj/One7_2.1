import streamlit as st
from datetime import datetime

from auth import initialize_session, load_user_context, has_cabinet
from database import (
    get_audit_logs,
    get_cabinet,
    get_cabinet_members,
    get_cabinet_settings,
    update_cabinet,
    update_member_role,
    upsert_cabinet_settings,
)

initialize_session()
load_user_context()

st.set_page_config(page_title="One7 — Paramètres", page_icon="⚙️", layout="wide")

if not has_cabinet():
    st.warning("Aucun cabinet actif.")
    st.stop()

cabinet = st.session_state.get("cabinet") or {}
cabinet_id = cabinet.get("id")
role = st.session_state.get("cabinet_role", "lecture")

if not cabinet_id:
    st.error("Cabinet introuvable dans la session.")
    st.stop()

can_manage = role in {"admin", "expert_comptable"}
can_write = role in {"admin", "expert_comptable", "comptable", "assistant"}

st.title("⚙️ Paramètres")
st.caption("Configuration du cabinet, des collaborateurs, des règles fiscales et de l'audit.")

tab_cabinet, tab_members, tab_fiscal, tab_ai, tab_audit = st.tabs([
    "🏢 Cabinet", "👥 Collaborateurs", "📊 Fiscalité", "🤖 IA", "🧾 Audit"
])

with tab_cabinet:
    current = get_cabinet(cabinet_id)
    if not current:
        st.error("Impossible de charger les informations du cabinet.")
    else:
        with st.form("cabinet_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Nom du cabinet", value=current.get("name") or "")
                legal_name = st.text_input("Raison sociale", value=current.get("legal_name") or "")
                ifu = st.text_input("IFU", value=current.get("ifu") or "")
                rccm = st.text_input("RCCM", value=current.get("rccm") or "")
            with c2:
                address = st.text_area("Adresse", value=current.get("address") or "")
                phone = st.text_input("Téléphone", value=current.get("phone") or "")
                email = st.text_input("Email", value=current.get("email") or "")
                currency = st.text_input("Devise", value=current.get("currency") or "XOF")

            submitted = st.form_submit_button(
                "💾 Enregistrer",
                type="primary",
                disabled=not can_manage,
            )
            if submitted:
                updated = update_cabinet(cabinet_id, {
                    "name": name.strip(),
                    "legal_name": legal_name.strip() or None,
                    "ifu": ifu.strip() or None,
                    "rccm": rccm.strip() or None,
                    "address": address.strip() or None,
                    "phone": phone.strip() or None,
                    "email": email.strip() or None,
                    "currency": currency.strip() or "XOF",
                })
                if updated:
                    st.session_state["cabinet"] = {**cabinet, **updated}
                    st.success("Informations du cabinet mises à jour.")
                else:
                    st.error("La mise à jour n'a pas retourné de données.")

with tab_members:
    st.info("Pour des raisons de sécurité, cette première version affiche l'identifiant utilisateur Supabase. L'invitation par email viendra dans l'étape suivante.")
    members = get_cabinet_members(cabinet_id)
    if not members:
        st.info("Aucun collaborateur trouvé.")
    else:
        for member in members:
            cols = st.columns([2.3, 1.4, 1.2])
            with cols[0]:
                st.code(member.get("user_id", "—"))
            with cols[1]:
                st.write(f"**{member.get('role', 'lecture')}**")
            with cols[2]:
                member_id = member.get("id")
                current_role = member.get("role", "lecture")
                roles = ["admin", "expert_comptable", "comptable", "assistant", "lecture"]
                new_role = st.selectbox(
                    "Rôle",
                    roles,
                    index=roles.index(current_role) if current_role in roles else 4,
                    key=f"role_{member_id}",
                    disabled=not can_manage,
                    label_visibility="collapsed",
                )
                if st.button("Changer", key=f"save_role_{member_id}", disabled=not can_manage):
                    # Évite une auto-réduction accidentelle de privilèges.
                    if member.get("user_id") == st.session_state.get("user", {}).get("id") and new_role != current_role:
                        st.warning("Ne modifiez pas votre propre rôle depuis cet écran.")
                    else:
                        updated = update_member_role(member_id, new_role)
                        if updated:
                            st.success("Rôle mis à jour.")
                            st.rerun()
                        else:
                            st.error("Échec de la mise à jour du rôle.")

with tab_fiscal:
    settings = get_cabinet_settings(cabinet_id)
    if settings is None:
        st.warning("La migration `supabase_parametres.sql` doit être appliquée dans Supabase.")
    else:
        with st.form("fiscal_settings_form"):
            c1, c2 = st.columns(2)
            with c1:
                vat = st.number_input(
                    "Taux TVA par défaut (%)",
                    min_value=0.0, max_value=100.0,
                    value=float(settings.get("vat_default_rate", 18)),
                    step=0.5,
                )
            with c2:
                aib = st.number_input(
                    "Taux AIB par défaut (%)",
                    min_value=0.0, max_value=100.0,
                    value=float(settings.get("aib_default_rate", 1)),
                    step=0.1,
                )
            st.caption("Ces valeurs sont des paramètres par défaut de l'application. Elles ne remplacent pas les règles fiscales applicables au client.")
            save = st.form_submit_button("💾 Enregistrer", disabled=not can_write)
            if save:
                if upsert_cabinet_settings(cabinet_id, {
                    "vat_default_rate": vat,
                    "aib_default_rate": aib,
                }):
                    st.success("Paramètres fiscaux enregistrés.")
                else:
                    st.error("Impossible d'enregistrer les paramètres.")

with tab_ai:
    settings = get_cabinet_settings(cabinet_id)
    if settings is None:
        st.warning("Appliquez d'abord `supabase_parametres.sql`.")
    else:
        st.warning("⚠️ L'IA doit rester contrôlée par le cabinet : aucune écriture comptable ou déclaration ne doit être validée automatiquement.")
        with st.form("ai_settings_form"):
            ai_enabled = st.toggle("Activer les fonctions IA", value=bool(settings.get("ai_enabled", False)))
            ai_auto = st.toggle(
                "Analyse automatique des documents importés",
                value=bool(settings.get("ai_auto_analysis", False)),
                disabled=not ai_enabled,
            )
            st.caption("La clé API Gemini doit rester dans les secrets de déploiement, jamais dans cette table.")
            save = st.form_submit_button("💾 Enregistrer", disabled=not can_manage)
            if save:
                if upsert_cabinet_settings(cabinet_id, {
                    "ai_enabled": ai_enabled,
                    "ai_auto_analysis": ai_auto,
                }):
                    st.success("Paramètres IA enregistrés.")
                else:
                    st.error("Impossible d'enregistrer les paramètres IA.")

with tab_audit:
    logs = get_audit_logs(cabinet_id, limit=100)
    if not logs:
        st.info("Aucun événement d'audit trouvé.")
    else:
        rows = []
        for log in logs:
            rows.append({
                "Date": log.get("created_at"),
                "Action": log.get("action"),
                "Table": log.get("table_name"),
                "Enregistrement": log.get("record_id"),
                "Utilisateur": log.get("user_id"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} événement(s) affiché(s).")

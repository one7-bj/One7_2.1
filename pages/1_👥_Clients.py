# ============================================================
# ONE7 V2.2
# 1_👥_Clients.py
# ============================================================

import streamlit as st

from auth import initialize_session, is_authenticated, has_cabinet, logout
from database import (
    get_supabase,
    get_clients,
    create_client,
    update_client,
    get_client_exercises,
    create_exercise,
)

st.set_page_config(
    page_title="One7 — Clients",
    page_icon="👥",
    layout="wide",
)

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

WRITE_ROLES = {"admin", "expert_comptable", "comptable", "assistant"}
ADMIN_ROLES = {"admin", "expert_comptable"}

with st.sidebar:
    st.markdown("### 📊 One7")
    st.caption(f"🏢 {cabinet.get('name', 'Cabinet')}")
    st.caption(f"Rôle : {role.replace('_', ' ').title()}")
    st.divider()
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()
    if st.button("🚪 Se déconnecter", use_container_width=True):
        logout()

st.title("👥 Clients")
st.caption("Gérez les dossiers clients et leurs exercices comptables.")
st.divider()

clients = get_clients(cabinet_id)

# ------------------------------------------------------------
# Résumé
# ------------------------------------------------------------
active_count = sum(1 for c in clients if c.get("status") == "actif")
inactive_count = sum(1 for c in clients if c.get("status") == "inactif")
archived_count = sum(1 for c in clients if c.get("status") == "archive")

c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Total", len(clients))
c2.metric("🟢 Actifs", active_count)
c3.metric("🟠 Inactifs", inactive_count)
c4.metric("⚫ Archivés", archived_count)

st.divider()

# ------------------------------------------------------------
# Création
# ------------------------------------------------------------
if role in WRITE_ROLES:
    with st.expander("➕ Ajouter un client", expanded=not clients):
        with st.form("create_client_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nom du client *", placeholder="Entreprise ABC")
                legal_name = st.text_input("Dénomination sociale", placeholder="ABC SARL")
                ifu = st.text_input("IFU")
                rccm = st.text_input("RCCM")
                activity = st.text_input("Activité", placeholder="Commerce, services...")

            with col2:
                tax_regime = st.text_input("Régime fiscal", placeholder="Réel normal")
                contact_name = st.text_input("Personne à contacter")
                phone = st.text_input("Téléphone")
                email = st.text_input("Email")
                address = st.text_area("Adresse", height=92)

            notes = st.text_area("Notes", height=90)

            submitted = st.form_submit_button(
                "Créer le client",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if not name.strip():
                    st.error("Le nom du client est obligatoire.")
                else:
                    ok, message = create_client(
                        cabinet_id=cabinet_id,
                        name=name,
                        legal_name=legal_name,
                        ifu=ifu,
                        rccm=rccm,
                        activity=activity,
                        tax_regime=tax_regime,
                        address=address,
                        phone=phone,
                        email=email,
                        contact_name=contact_name,
                        notes=notes,
                    )
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
else:
    st.info("Votre rôle est en lecture seule : vous pouvez consulter les clients, mais pas en créer ni les modifier.")

# ------------------------------------------------------------
# Recherche
# ------------------------------------------------------------
search = st.text_input(
    "🔎 Rechercher un client",
    placeholder="Nom, IFU, RCCM, téléphone...",
)

filtered = clients
if search.strip():
    term = search.strip().lower()
    filtered = [
        c for c in clients
        if any(term in str(c.get(field) or "").lower() for field in (
            "name", "legal_name", "ifu", "rccm", "phone", "email", "activity"
        ))
    ]

st.markdown(f"### Liste des clients ({len(filtered)})")

if not filtered:
    st.info("Aucun client ne correspond à votre recherche.")
    st.stop()

# ------------------------------------------------------------
# Dossiers clients
# ------------------------------------------------------------
for client in filtered:
    client_id = client.get("id")
    status = client.get("status") or "actif"
    status_label = {
        "actif": "🟢 Actif",
        "inactif": "🟠 Inactif",
        "archive": "⚫ Archivé",
    }.get(status, status)

    with st.expander(f"**{client.get('name', 'Client sans nom')}**  ·  {status_label}"):
        top1, top2, top3 = st.columns(3)
        top1.write(f"**IFU :** {client.get('ifu') or '—'}")
        top2.write(f"**RCCM :** {client.get('rccm') or '—'}")
        top3.write(f"**Activité :** {client.get('activity') or '—'}")

        info1, info2 = st.columns(2)
        with info1:
            st.write(f"**Dénomination :** {client.get('legal_name') or '—'}")
            st.write(f"**Régime fiscal :** {client.get('tax_regime') or '—'}")
            st.write(f"**Contact :** {client.get('contact_name') or '—'}")
        with info2:
            st.write(f"**Téléphone :** {client.get('phone') or '—'}")
            st.write(f"**Email :** {client.get('email') or '—'}")
            st.write(f"**Adresse :** {client.get('address') or '—'}")

        if client.get("notes"):
            st.caption(f"📝 {client['notes']}")

        exercises = get_client_exercises(client_id)
        st.markdown("#### 📅 Exercices comptables")

        if exercises:
            exercise_rows = [
                {
                    "Année": e.get("year"),
                    "Début": e.get("start_date"),
                    "Fin": e.get("end_date"),
                    "Statut": e.get("status"),
                }
                for e in exercises
            ]
            st.dataframe(exercise_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun exercice comptable enregistré pour ce client.")

        if role in WRITE_ROLES:
            with st.expander("➕ Créer un exercice"):
                with st.form(f"exercise_form_{client_id}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        year = st.number_input("Année", min_value=2000, max_value=2100, value=2026, step=1)
                    with col2:
                        start_date = st.date_input("Date de début")
                    with col3:
                        end_date = st.date_input("Date de fin")

                    submitted = st.form_submit_button("Créer l'exercice", use_container_width=True)
                    if submitted:
                        if end_date < start_date:
                            st.error("La date de fin doit être postérieure ou égale à la date de début.")
                        else:
                            ok, message = create_exercise(
                                client_id=client_id,
                                year=int(year),
                                start_date=start_date,
                                end_date=end_date,
                            )
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

        if role in WRITE_ROLES:
            with st.expander("✏️ Modifier le client"):
                with st.form(f"edit_client_{client_id}"):
                    new_status = st.selectbox(
                        "Statut",
                        ["actif", "inactif", "archive"],
                        index=["actif", "inactif", "archive"].index(status) if status in {"actif", "inactif", "archive"} else 0,
                    )
                    new_phone = st.text_input("Téléphone", value=client.get("phone") or "")
                    new_email = st.text_input("Email", value=client.get("email") or "")
                    new_address = st.text_area("Adresse", value=client.get("address") or "")
                    new_notes = st.text_area("Notes", value=client.get("notes") or "")

                    submitted = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)
                    if submitted:
                        ok, message = update_client(
                            client_id=client_id,
                            cabinet_id=cabinet_id,
                            values={
                                "status": new_status,
                                "phone": new_phone,
                                "email": new_email,
                                "address": new_address,
                                "notes": new_notes,
                            },
                        )
                        if ok:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

        if role in ADMIN_ROLES:
            st.caption("💡 La suppression définitive n'est pas proposée ici : l'archivage permet de conserver l'historique comptable.")

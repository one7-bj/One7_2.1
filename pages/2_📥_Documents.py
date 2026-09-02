# ============================================================
# ONE7 V2.2
# 2_📥_Documents.py
# ============================================================

import io
import mimetypes
import re
import uuid
from datetime import date

import streamlit as st

from auth import initialize_session, is_authenticated, has_cabinet, logout
from ai_engine import gemini_available, analyze_invoice_text, merge_ai_result, normalize_controls
from ocr_engine import extract_image_text, extract_pdf_ocr, tesseract_available

from database import (
    get_clients,
    get_client_exercises,
    get_documents,
    find_duplicate_document,
    create_document,
    update_document,
    upload_document_file,
    get_chart_of_accounts,
    create_accounting_control,
)

st.set_page_config(page_title="One7 — Documents", page_icon="📥", layout="wide")
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

with st.sidebar:
    st.markdown("### 📊 One7")
    st.caption(f"🏢 {cabinet.get('name', 'Cabinet')}")
    st.caption(f"Rôle : {role.replace('_', ' ').title()}")
    st.divider()
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()
    if st.button("🚪 Se déconnecter", use_container_width=True):
        logout()


def clean_number(value: str):
    if not value:
        return None
    value = value.replace("\u00a0", " ").replace(" ", "").replace("FCFA", "").replace("XOF", "")
    value = value.replace(".", "").replace(",", ".")
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def first_match(text: str, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.M)
        if match:
            return match.group(1).strip()
    return None


def extract_pdf_text(file_bytes: bytes):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [(page.extract_text() or "") for page in pdf.pages]
        return "\n".join(pages).strip()
    except Exception:
        return ""


def extract_invoice_fields(file_name: str, file_bytes: bytes):
    """Extraction légère et transparente. Elle ne remplace pas encore l'OCR/IA."""
    text = ""
    if file_name.lower().endswith(".pdf"):
        text = extract_pdf_text(file_bytes)

    fields = {
        "invoice_number": first_match(text, [
            r"(?:facture|invoice|n[°o]|no)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,})",
        ]),
        "invoice_date": None,
        "supplier_name": first_match(text, [
            r"(?:fournisseur|supplier)\s*[:\-]\s*(.+)",
        ]),
        "supplier_ifu": first_match(text, [r"(?:ifu|IFU)\s*[:#-]?\s*([A-Z0-9-]{5,})"]),
        "amount_ht": None,
        "vat_amount": None,
        "amount_ttc": None,
        "vat_rate": None,
        "extracted_data": {"text_available": bool(text), "text_length": len(text)},
    }

    raw_date = first_match(text, [
        r"(?:date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ])
    if raw_date:
        parts = re.split(r"[/-]", raw_date)
        try:
            d, m, y = map(int, parts)
            if y < 100:
                y += 2000
            fields["invoice_date"] = date(y, m, d).isoformat()
        except ValueError:
            pass

    patterns = {
        "amount_ht": [r"(?:total\s*ht|montant\s*ht|ht)\s*[:=]?\s*([0-9][0-9 .]*[,\.]?[0-9]*)"],
        "vat_amount": [r"(?:tva|vat)\s*(?:montant)?\s*[:=]?\s*([0-9][0-9 .]*[,\.]?[0-9]*)"],
        "amount_ttc": [r"(?:total\s*ttc|montant\s*ttc|ttc|total)\s*[:=]?\s*([0-9][0-9 .]*[,\.]?[0-9]*)"],
        "vat_rate": [r"(?:tva|vat)\s*[:=]?\s*(\d{1,2}(?:[,.]\d+)?)\s*%"],
    }
    for key, pats in patterns.items():
        value = first_match(text, pats)
        if value:
            fields[key] = clean_number(value)

    if fields["amount_ht"] is not None and fields["vat_amount"] is not None and fields["amount_ttc"] is None:
        fields["amount_ttc"] = round(fields["amount_ht"] + fields["vat_amount"], 2)

    if fields["amount_ttc"] is not None and fields["amount_ht"] is not None and fields["vat_rate"] is None and fields["amount_ht"]:
        fields["vat_rate"] = round((fields["amount_ttc"] - fields["amount_ht"]) / fields["amount_ht"] * 100, 4)

    fields["extraction_confidence"] = 70 if text else None
    return fields, text


st.title("📥 Documents")
st.caption("Importez les pièces du dossier, contrôlez les doublons et préparez leur traitement comptable.")
if tesseract_available():
    st.caption("🖨️ OCR disponible : les scans PDF et images peuvent être analysés.")
else:
    st.caption("🖨️ OCR non installé : les PDF textuels restent exploitables.")

if gemini_available():
    st.success("🤖 IA activée : pré-analyse des PDF textuels, contrôles et suggestion d’imputation.")
else:
    st.info("🤖 IA non configurée : ajoutez GEMINI_API_KEY dans les secrets pour activer la pré-analyse.")
st.divider()

clients = get_clients(cabinet_id)
client_options = {c["name"]: c["id"] for c in clients}

# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------
if role in WRITE_ROLES:
    with st.expander("➕ Importer un document", expanded=not bool(get_documents(cabinet_id, limit=1))):
        if not clients:
            st.warning("Créez d'abord un client dans le module Clients.")
        else:
            with st.form("document_upload_form"):
                client_name = st.selectbox("Client *", list(client_options.keys()))
                client_id = client_options[client_name]
                exercises = get_client_exercises(client_id)
                exercise_options = {"Aucun exercice": None}
                exercise_options.update({f"{e['year']} · {e['status']}": e["id"] for e in exercises})
                exercise_label = st.selectbox("Exercice", list(exercise_options.keys()))
                document_type = st.selectbox("Type de document", ["facture", "avoir", "note_de_credit", "recu", "autre"])
                uploaded = st.file_uploader("Fichier", type=["pdf", "png", "jpg", "jpeg"], help="PDF ou image. L'analyse automatique des PDF textuels est activée.")
                submitted = st.form_submit_button("⬆️ Importer et analyser", type="primary", use_container_width=True)

            if submitted:
                if uploaded is None:
                    st.error("Sélectionnez un fichier.")
                else:
                    file_bytes = uploaded.getvalue()
                    extracted, raw_text = extract_invoice_fields(uploaded.name, file_bytes)

                    # Si le PDF est scanné ou si le fichier est une image, tenter l'OCR.
                    ocr_message = ""
                    lower_name = uploaded.name.lower()
                    if not raw_text and tesseract_available():
                        if lower_name.endswith((".png", ".jpg", ".jpeg")):
                            raw_text, ocr_message = extract_image_text(file_bytes)
                        elif lower_name.endswith(".pdf"):
                            raw_text, ocr_message = extract_pdf_ocr(file_bytes)
                    elif not raw_text:
                        ocr_message = "OCR non disponible sur ce serveur."


                    # Pré-analyse IA facultative : elle enrichit le dossier mais ne valide jamais.
                    ai_result = None
                    if raw_text and gemini_available():
                        try:
                            ai_result = analyze_invoice_text(
                                raw_text,
                                known_fields=extracted,
                                chart_accounts=get_chart_of_accounts(cabinet_id, limit=300),
                            )
                            extracted = merge_ai_result(extracted, ai_result)
                        except Exception as exc:
                            extracted["ai_notes"] = f"Analyse IA indisponible : {exc}"
                            extracted.setdefault("extracted_data", {})["ai_error"] = str(exc)

                    duplicate = find_duplicate_document(
                        cabinet_id,
                        client_id,
                        extracted.get("invoice_number"),
                        extracted.get("supplier_ifu"),
                        extracted.get("supplier_name"),
                    )
                    if duplicate:
                        st.error(
                            f"⚠️ Doublon probable : {duplicate.get('file_name')} "
                            f"— facture {duplicate.get('invoice_number') or 'sans numéro'}.")
                    else:
                        storage_path = f"{cabinet_id}/{client_id}/{uuid.uuid4()}_{uploaded.name}"
                        content_type = uploaded.type or mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
                        storage_ok, storage_result = upload_document_file(storage_path, file_bytes, content_type)
                        if not storage_ok:
                            st.error(f"Le fichier n'a pas pu être envoyé au stockage Supabase : {storage_result}")
                            st.info("Vérifiez que le bucket privé 'documents' a été créé avec le script SQL fourni dans le pack.")
                        else:
                            user_id = getattr(user, "id", None) if user else None
                            status = "analyse" if raw_text else "importe"
                            ok, row, message = create_document(
                                cabinet_id=cabinet_id,
                                client_id=client_id,
                                exercise_id=exercise_options[exercise_label],
                                uploaded_by=user_id,
                                file_name=uploaded.name,
                                storage_path=storage_path,
                                document_type=document_type,
                                status=status,
                                fields=extracted,
                            )
                            if ok:
                                if ocr_message:
                                    st.caption(f"🔎 {ocr_message}")
                                if ai_result:
                                    for control in normalize_controls(ai_result):
                                        create_accounting_control(
                                            cabinet_id=cabinet_id,
                                            client_id=client_id,
                                            document_id=row.get("id"),
                                            title=control["title"],
                                            description=control["description"],
                                            severity=control["severity"],
                                        )
                                    st.success("Document importé + pré-analyse IA terminée.")
                                    suggestion = ai_result.get("accounting_suggestion") or {}
                                    if suggestion.get("account_number"):
                                        st.info(
                                            f"💡 Imputation suggérée : {suggestion.get('account_number')} — "
                                            f"{suggestion.get('account_name') or 'compte'} "
                                            f"(confiance {suggestion.get('confidence', 0)} %). "
                                            "Validation humaine obligatoire."
                                        )
                                elif raw_text:
                                    st.success("Document importé avec analyse locale.")
                                    st.info("Vérifiez les champs extraits avant validation.")
                                else:
                                    st.success("Document importé.")
                                    st.info("OCR/IA indisponible pour ce fichier ou non configurée.")
                                st.rerun()
                            else:
                                st.error(message)

else:
    st.info("Votre rôle est en lecture seule : vous pouvez consulter les documents, mais pas en importer ni les modifier.")

# ------------------------------------------------------------
# FILTRES / LISTE
# ------------------------------------------------------------
all_documents = get_documents(cabinet_id, limit=200)

f1, f2, f3 = st.columns(3)
with f1:
    client_filter_label = st.selectbox("Client", ["Tous"] + list(client_options.keys()))
with f2:
    status_filter = st.selectbox("Statut", ["Tous", "importe", "analyse", "a_controler", "valide", "rejete", "archive"])
with f3:
    search = st.text_input("🔎 Recherche", placeholder="fichier, fournisseur, facture...")

filtered = all_documents
if client_filter_label != "Tous":
    cid = client_options[client_filter_label]
    filtered = [d for d in filtered if d.get("client_id") == cid]
if status_filter != "Tous":
    filtered = [d for d in filtered if d.get("status") == status_filter]
if search.strip():
    term = search.strip().lower()
    filtered = [
        d for d in filtered
        if any(term in str(d.get(k) or "").lower() for k in ("file_name", "invoice_number", "supplier_name", "supplier_ifu"))
    ]

st.markdown(f"### 📚 Documents ({len(filtered)})")

if not filtered:
    st.info("Aucun document ne correspond aux filtres sélectionnés.")
    st.stop()

for doc in filtered:
    client = doc.get("clients") or {}
    client_display = client.get("name") if isinstance(client, dict) else "—"
    status = doc.get("status") or "importe"
    label = {
        "importe": "📥 Importé",
        "analyse": "🔎 Analysé",
        "a_controler": "🟠 À contrôler",
        "valide": "🟢 Validé",
        "rejete": "🔴 Rejeté",
        "archive": "⚫ Archivé",
    }.get(status, status)

    with st.expander(f"{doc.get('file_name') or 'Document'} · {client_display} · {label}"):
        c1, c2, c3, c4 = st.columns(4)
        c1.write(f"**Facture :** {doc.get('invoice_number') or '—'}")
        c2.write(f"**Date :** {doc.get('invoice_date') or '—'}")
        c3.write(f"**HT :** {doc.get('amount_ht') or 0:,.2f} FCFA".replace(",", " "))
        c4.write(f"**TTC :** {doc.get('amount_ttc') or 0:,.2f} FCFA".replace(",", " "))

        st.write(f"**Fournisseur :** {doc.get('supplier_name') or '—'} · **IFU :** {doc.get('supplier_ifu') or '—'}")
        st.write(f"**Confiance extraction :** {doc.get('extraction_confidence') if doc.get('extraction_confidence') is not None else '—'} %")

        if role in WRITE_ROLES:
            with st.form(f"edit_document_{doc['id']}"):
                e1, e2, e3 = st.columns(3)
                with e1:
                    new_status = st.selectbox("Statut", ["importe", "analyse", "a_controler", "valide", "rejete", "archive"], index=["importe", "analyse", "a_controler", "valide", "rejete", "archive"].index(status))
                    new_invoice = st.text_input("N° facture", value=doc.get("invoice_number") or "")
                with e2:
                    new_supplier = st.text_input("Fournisseur", value=doc.get("supplier_name") or "")
                    new_ifu = st.text_input("IFU fournisseur", value=doc.get("supplier_ifu") or "")
                with e3:
                    new_ht = st.number_input("HT", min_value=0.0, value=float(doc.get("amount_ht") or 0), step=100.0)
                    new_vat = st.number_input("TVA", min_value=0.0, value=float(doc.get("vat_amount") or 0), step=100.0)
                    new_ttc = st.number_input("TTC", min_value=0.0, value=float(doc.get("amount_ttc") or 0), step=100.0)
                notes = st.text_area("Notes de validation", value=doc.get("validation_notes") or "")
                save = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
                if save:
                    ok, message = update_document(
                        doc["id"], cabinet_id,
                        {
                            "status": new_status,
                            "invoice_number": new_invoice.strip() or None,
                            "supplier_name": new_supplier.strip() or None,
                            "supplier_ifu": new_ifu.strip() or None,
                            "amount_ht": new_ht,
                            "vat_amount": new_vat,
                            "amount_ttc": new_ttc,
                            "validation_notes": notes.strip() or None,
                        },
                    )
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

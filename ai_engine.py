import json
import os
import re
from typing import Any, Dict, List, Optional


def _get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def gemini_available() -> bool:
    return bool(_get_secret("GEMINI_API_KEY"))


def _model():
    import google.generativeai as genai
    api_key = _get_secret("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY n'est pas configurée.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(_get_secret("GEMINI_MODEL", "gemini-2.5-flash"))


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("La réponse IA ne contient pas de JSON exploitable.")
    return json.loads(text[start:end + 1])


def analyze_invoice_text(
    text: str,
    known_fields: Optional[Dict[str, Any]] = None,
    chart_accounts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Aucun texte exploitable n'est disponible.")

    known_fields = known_fields or {}
    accounts = [
        {"account_number": a.get("account_number"),
         "account_name": a.get("account_name"),
         "account_type": a.get("account_type")}
        for a in (chart_accounts or [])[:300]
    ]

    prompt = f"""
Tu es un assistant de pré-comptabilisation pour un cabinet comptable.
Analyse la pièce fournie sans inventer d'information.
Les suggestions comptables doivent choisir UNIQUEMENT parmi les comptes fournis.
Une suggestion IA n'est jamais une validation.

Champs déjà extraits:
{json.dumps(known_fields, ensure_ascii=False)}

Plan comptable disponible:
{json.dumps(accounts, ensure_ascii=False)}

Retourne STRICTEMENT un objet JSON:
{{
  "invoice_number": null,
  "invoice_date": null,
  "supplier_name": null,
  "supplier_ifu": null,
  "customer_name": null,
  "customer_ifu": null,
  "amount_ht": null,
  "vat_amount": null,
  "amount_ttc": null,
  "vat_rate": null,
  "aib_rate": null,
  "aib_amount": null,
  "confidence": 0,
  "anomalies": [
    {{"severity": "info|warning|critical", "title": "...", "description": "..."}}
  ],
  "accounting_suggestion": {{
    "account_number": null,
    "account_name": null,
    "reason": "...",
    "confidence": 0
  }},
  "summary": "..."
}}

Contrôles minimum:
- HT + TVA ≈ TTC si disponibles.
- TVA / HT cohérente avec le taux indiqué.
- Signaler les champs essentiels absents.
- Ne jamais inventer un compte absent du plan comptable.

Texte de la pièce:
---BEGIN DOCUMENT---
{text[:30000]}
---END DOCUMENT---
"""
    result = _model().generate_content(prompt)
    return _extract_json(getattr(result, "text", "") or "")


def merge_ai_result(local_fields: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(local_fields)
    for key in [
        "invoice_number", "invoice_date", "supplier_name", "supplier_ifu",
        "customer_name", "customer_ifu", "amount_ht", "vat_amount",
        "amount_ttc", "vat_rate", "aib_rate", "aib_amount",
    ]:
        value = ai_result.get(key)
        if value not in (None, ""):
            merged[key] = value
    merged["extraction_confidence"] = ai_result.get(
        "confidence", merged.get("extraction_confidence")
    )
    merged["ai_notes"] = ai_result.get("summary")
    extracted = merged.get("extracted_data") or {}
    extracted["ai_analysis"] = ai_result
    merged["extracted_data"] = extracted
    return merged


def normalize_controls(ai_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for item in ai_result.get("anomalies") or []:
        severity = item.get("severity", "warning")
        if severity not in {"info", "warning", "critical"}:
            severity = "warning"
        result.append({
            "severity": severity,
            "title": item.get("title") or "Anomalie détectée par IA",
            "description": item.get("description") or "Vérification humaine requise.",
        })
    return result

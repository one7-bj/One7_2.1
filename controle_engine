from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def _dec(value: Any):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def run_document_controls(fields: Dict[str, Any]) -> List[Dict[str, str]]:
    """Contrôles déterministes avant toute validation humaine."""
    controls = []

    invoice = fields.get("invoice_number")
    ht = _dec(fields.get("amount_ht"))
    vat = _dec(fields.get("vat_amount"))
    ttc = _dec(fields.get("amount_ttc"))
    rate = _dec(fields.get("vat_rate"))

    if not invoice:
        controls.append({"severity": "warning", "title": "Numéro de facture absent",
                         "description": "Vérifier la pièce et compléter le numéro si nécessaire."})

    if ht is not None and vat is not None and ttc is not None:
        if abs((ht + vat) - ttc) > Decimal("1.00"):
            controls.append({"severity": "critical", "title": "Incohérence HT/TVA/TTC",
                             "description": "Le total HT + TVA ne correspond pas au TTC extrait."})

    if ht and vat is not None and rate is not None:
        expected = ht * rate / Decimal("100")
        if abs(expected - vat) > max(Decimal("1.00"), abs(vat) * Decimal("0.02")):
            controls.append({"severity": "warning", "title": "TVA potentiellement incohérente",
                             "description": "Le montant de TVA ne correspond pas approximativement au taux indiqué."})

    required = {
        "supplier_name": "Fournisseur",
        "invoice_date": "Date de facture",
        "amount_ttc": "Montant TTC",
    }
    for key, label in required.items():
        if fields.get(key) in (None, ""):
            controls.append({"severity": "warning", "title": f"{label} absent",
                             "description": f"Le champ {label} doit être vérifié avant validation."})

    return controls

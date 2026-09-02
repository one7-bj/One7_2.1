# One7 V2.2 — Étape Comptabilité

Cette étape ajoute le module `3_📒_Comptabilite.py` et les fonctions Supabase correspondantes dans `database.py`.

Fonctions :
- plan comptable par cabinet ;
- journaux par cabinet ;
- création d'écritures en brouillon ;
- lignes débit/crédit ;
- contrôle d'équilibre avant enregistrement ;
- soumission pour validation ;
- validation des écritures équilibrées ;
- filtres client/exercice/statut.

Le module s'appuie sur les tables `chart_of_accounts`, `journals`, `accounting_entries` et `accounting_entry_lines` du schéma One7 V2.2.

Important : le schéma SQL V2.2 consolidé doit être appliqué dans Supabase avant utilisation complète.

# One7 V2.2 — Paramètres

Cette étape ajoute le module `5_⚙️_Parametres.py`.

## Installation

1. Garder les fichiers Python existants de One7.
2. Ajouter `database_parametres.py`, `config.py` et `5_⚙️_Parametres.py`.
3. Exécuter `supabase_parametres.sql` après le schéma V2.2 consolidé.
4. Conserver `.streamlit/secrets.toml` avec `SUPABASE_URL` et `SUPABASE_KEY`.

## Contenu

- Informations du cabinet.
- Consultation et changement des rôles des collaborateurs autorisés.
- Paramètres TVA/AIB par défaut.
- Activation contrôlée des fonctions IA.
- Consultation de l'audit.

Les taux fiscaux sont des paramètres applicatifs : ils ne constituent pas à eux seuls une implémentation complète de la réglementation fiscale béninoise.

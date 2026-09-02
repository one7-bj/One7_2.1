# One7 2.1.1

Plateforme de gestion comptable pour cabinets — Streamlit + Supabase.

## Structure

- `app.py` : authentification, sélection du cabinet et dashboard.
- `auth.py` : session, connexion et contexte multi-cabinet.
- `database.py` : accès Supabase et fonctions de données.
- `config.py` : configuration One7.
- `pages/` : Clients, Documents, Comptabilité, Fiscalité, Paramètres.
- `supabase/one7_schema.sql` : schéma multi-cabinet + RLS + RPC.

## Configuration

Créer `.streamlit/secrets.toml` :

```toml
SUPABASE_URL = "https://votre-projet.supabase.co"
SUPABASE_KEY = "votre-cle-publique"
```

Ne jamais committer ce fichier. Le `.gitignore` fourni l'exclut.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Migration

1. Exécuter `supabase/one7_schema.sql` dans le SQL Editor Supabase.
2. Remplacer les fichiers Python correspondants.
3. Conserver les anciens modules d'import/imputation/déclaration puis les reconnecter progressivement aux nouvelles tables `clients`, `documents`, `journal_entries` et `tax_declarations`.

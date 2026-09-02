# One7 V2.5.1 — Streamlit Community Cloud

Version optimisée pour un déploiement depuis GitHub avec Streamlit Community Cloud.

## 1. Structure GitHub

Le dépôt doit contenir `app.py` à la racine et le dossier `pages/` au même niveau.

## 2. Dépendances

- `requirements.txt` : dépendances Python.
- `packages.txt` : dépendances Linux nécessaires à Tesseract OCR.

Streamlit Community Cloud installe automatiquement ces dépendances lors du déploiement.

## 3. Secrets

Ne jamais ajouter `.streamlit/secrets.toml` à GitHub.

Dans Streamlit Community Cloud : App → Settings → Secrets, ajouter :

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

# Facultatif : IA Gemini
GEMINI_API_KEY = "YOUR_GEMINI_KEY"
GEMINI_MODEL = "gemini-2.5-flash"
```

## 4. Supabase

Dans SQL Editor, exécuter dans cet ordre :

1. `One7_V2.2_schema_consolide.sql`
2. `supabase_storage_documents.sql`
3. `supabase_parametres.sql`

Les anciens jeux de données de test ne sont pas nécessaires pour cette version.

## 5. Déploiement

Sur https://share.streamlit.io :

1. Create app
2. sélectionner le dépôt GitHub
3. sélectionner la branche
4. fichier principal : `app.py`
5. Advanced settings → choisir la version Python souhaitée
6. renseigner les Secrets
7. Deploy

## 6. Vérifications après déploiement

1. inscription / connexion
2. création du cabinet
3. affichage du Dashboard
4. présence de Paramètres
5. création d'un client
6. création d'un exercice
7. import d'un PDF
8. test OCR sur image/PDF sans texte
9. test contrôles
10. test IA si Gemini est activé
11. création d'une écriture équilibrée
12. test fiscalité

## 7. Mise à jour

Le dépôt GitHub est la source de l'application. Après un commit/push, Community Cloud redéploie automatiquement l'application ; une modification des dépendances déclenche une réinstallation des dépendances.

## 8. Important

Les fichiers SQL sont à exécuter dans Supabase, pas dans Streamlit Cloud.
Les clés Supabase/Gemini restent dans les Secrets de Community Cloud et ne sont jamais commités.

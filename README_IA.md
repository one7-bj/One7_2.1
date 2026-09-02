# One7 V2.3 — Pré-comptabilisation IA

Chaîne : PDF textuel → extraction locale → Gemini → contrôles → suggestion d'imputation → validation humaine.

Secrets :
```toml
GEMINI_API_KEY = "..."
GEMINI_MODEL = "gemini-2.5-flash"
```

Principes :
- l'IA ne crée pas d'écriture comptable ;
- l'IA ne valide pas une pièce ;
- les comptes proposés sont limités au plan comptable du cabinet ;
- les anomalies sont enregistrées comme contrôles ;
- l'OCR des images reste une étape séparée.

Installation :
1. Ajouter `ai_engine.py`.
2. Remplacer `2_📥_Documents.py`.
3. Utiliser le `database.py` fourni ou fusionner sa nouvelle fonction.
4. Ajouter `GEMINI_API_KEY` dans les secrets.

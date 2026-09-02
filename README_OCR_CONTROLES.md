# One7 V2.4 — OCR + contrôles déterministes

Cette version ajoute :

1. OCR Tesseract pour images PNG/JPG/JPEG.
2. OCR de PDF scannés par rendu des pages.
3. Contrôles déterministes HT/TVA/TTC et champs essentiels.
4. Conservation du principe human-in-the-loop : aucun document ni aucune écriture n'est validé automatiquement.

## Serveur

Python :
- Pillow
- pytesseract

Système :
- Tesseract OCR doit être installé sur le serveur.
- Les langues `fra` et `eng` sont recommandées.

Si Tesseract n'est pas disponible, One7 continue à fonctionner pour les PDF contenant déjà du texte.

## Flux cible

PDF/image
→ extraction texte native
→ OCR si nécessaire
→ contrôles déterministes
→ Gemini si configuré
→ anomalies
→ suggestion d'imputation
→ validation humaine
→ écriture comptable.

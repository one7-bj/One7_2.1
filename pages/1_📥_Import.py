import streamlit as st
import pandas as pd
import json, re, pdfplumber
import google.generativeai as genai
from supabase import create_client

st.header("📥 Import des Factures PDF/Photos")

user_id = st.session_state.user.id
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3.6-flash')

# Paramètres
type_doc_choisi = st.sidebar.selectbox("Type de document", ["Facture d'achat", "Facture de vente", "Relevé bancaire"])
mapping_journal = {"Facture d'achat": "ACHAT", "Facture de vente": "VENTE", "Relevé bancaire": "BANQUE"}
journal_defaut = mapping_journal[type_doc_choisi]

def sauvegarder_dans_db(resultats):
    if resultats:
        df_doc = pd.DataFrame(resultats)
        df_doc['user_id'] = user_id
        df_doc = df_doc.rename(columns={
            "N° Pièce": "n_piece", "Date": "date", "Journal": "journal", "Tiers": "tiers",
            "Libellé": "libelle", "N°IFU": "nifu", "HT": "ht", "TVA 18%": "tva",
            "AIB": "aib", "Taux AIB": "taux_aib", "TTC": "ttc", "Type Doc": "type_doc", "Fichier": "fichier"
        })
        df_doc = df_doc.drop_duplicates(subset=['user_id', 'n_piece'])
        supabase.table('documents').upsert(df_doc.to_dict('records'), on_conflict='user_id,n_piece').execute()
        st.toast("✅ Sauvegardé sur le Cloud")

fichiers = st.file_uploader(f"Charge tes documents", type=["pdf", "png", "jpg"], accept_multiple_files=True)
if st.button("🚀 Lancer le traitement", type="primary"):
    if fichiers:
        resultats_detail = st.session_state.get('resultats_detail', []).copy()
        progress = st.progress(0)
        for i, fichier in enumerate(fichiers):
            file_bytes = fichier.read()
            prompt = """Extrait en JSON: {"n_facture": "", "date": "JJ/MM/AAAA", "fournisseur": "", "nifu": "", "libelle": "", "type_operation": "biens", "ht": 0, "tva": 0, "ttc": 0}"""
            response = model.generate_content([prompt, {"mime_type": fichier.type, "data": file_bytes}])
            try: data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
            except: data = {"n_facture": fichier.name, "libelle": "Erreur extraction"}

            resultats_detail.append({
                "Type Doc": type_doc_choisi, "Journal": journal_defaut, "Fichier": fichier.name,
                "N° Pièce": data.get("n_facture", "N/A"), "Date": data.get("date", "01/01/2026"),
                "Tiers": data.get("fournisseur", ""), "Libellé": data.get("libelle", ""),
                "N°IFU": data.get("nifu", ""), "HT": data.get("ht", 0.0),
                "TVA 18%": data.get("tva", 0.0), "AIB": 0.0, "Taux AIB": 0.0, "TTC": data.get("ttc", 0.0)
            })
            progress.progress((i+1)/len(fichiers))
        st.session_state.resultats_detail = resultats_detail
        sauvegarder_dans_db(resultats_detail)
        st.success(f"{len(fichiers)} documents traités et sauvegardés!")

if st.session_state.get('resultats_detail'):
    st.dataframe(pd.DataFrame(st.session_state.resultats_detail), use_container_width=True, hide_index=True)

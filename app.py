import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re
import pdfplumber
from datetime import datetime
import io
from supabase import create_client, Client # pip install supabase

# === 0. CONFIG + CONNEXION SUPABASE ===
st.set_page_config(page_title="One7 Pro - TVA & AIB Bénin", page_icon="🧾", layout="wide")
st.markdown("""<style>.stButton>button {background-color: #004AAD; color: white; border-radius: 8px;}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# === 1. GESTION LOGIN / SIGNUP ===
def auth_page():
    st.title("🧾 One7 Pro - Connexion")
    tab1, tab2 = st.tabs(["Se Connecter", "Créer un Compte"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e: st.error(f"Erreur: {e}")
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Mot de passe", type="password", key="signup_pass")
        nom_cabinet = st.text_input("Nom du Cabinet")
        if st.button("Créer le compte"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                supabase.table('profiles').insert({"id": res.user.id, "email": email, "nom_cabinet": nom_cabinet}).execute()
                st.success("Compte créé! Connecte-toi maintenant.")
            except Exception as e: st.error(f"Erreur: {e}")

if 'user' not in st.session_state:
    try:
        st.session_state.user = supabase.auth.get_user().user
    except: st.session_state.user = None

if not st.session_state.user:
    auth_page()
    st.stop() # Bloque tout si pas connecté

# === SI CONNECTE : ON AFFICHE L'APP ===
user_id = st.session_state.user.id
st.sidebar.success(f"Connecté: {st.session_state.user.email}")
if st.sidebar.button("Se déconnecter"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

st.title("🧾 One7 Pro - Déclaration TVA & AIB Bénin")
st.caption("Version Cloud Supabase - Multi-utilisateurs")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3.6-flash')

# === 2. DB FUNCTIONS SUPABASE ===
def sauvegarder_dans_db():
    if st.session_state.resultats_detail:
        df_doc = pd.DataFrame(st.session_state.resultats_detail)
        df_doc['user_id'] = user_id # CRITIQUE : on tag les données
        df_doc = df_doc.rename(columns={"N° Pièce": "n_piece", "Date": "date", "Journal": "journal", "Tiers": "tiers", "Libellé": "libelle", "N°IFU": "nifu", "HT": "ht", "TVA 18%": "tva", "AIB": "aib", "Taux AIB": "taux_aib", "TTC": "ttc", "Type Doc": "type_doc"})
        supabase.table('documents').upsert(df_doc.to_dict('records'), on_conflict='user_id,n_piece').execute()

    if st.session_state.imputations_epinglees:
        df_imp = pd.DataFrame(st.session_state.imputations_epinglees)
        df_imp['user_id'] = user_id
        df_imp = df_imp.rename(columns={"Numéro Pièce": "n_piece"})
        supabase.table('imputations').upsert(df_imp.to_dict('records')).execute()
    st.toast("✅ Sauvegardé sur le Cloud")

def charger_depuis_db():
    res_doc = supabase.table('documents').select("*").eq('user_id', user_id).execute()
    res_imp = supabase.table('imputations').select("*").eq('user_id', user_id).execute()
    if res_doc.data:
        st.session_state.resultats_detail = pd.DataFrame(res_doc.data).rename(columns={"n_piece": "N° Pièce", "date": "Date"}).to_dict('records')
    if res_imp.data:
        st.session_state.imputations_epinglees = pd.DataFrame(res_imp.data).rename(columns={"n_piece": "Numéro Pièce"}).to_dict('records')

# === SESSION STATE ===
if 'resultats_detail' not in st.session_state: st.session_state.resultats_detail = []
if 'imputations_epinglees' not in st.session_state: st.session_state.imputations_epinglees = []
charger_depuis_db()

# === 3. PLAN COMPTABLE CORRIGE : N'AFFICHE PLUS EN 4 CHIFFRES ===
@st.cache_data
def charger_plan_comptable(uploaded_file):
    plan = {}
    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                texte = page.extract_text()
                matches = re.findall(r'(\d{3,8})\s+([A-ZÉÈÀÂÔÙa-zéèàâôù0-9\s\-\'\.]+)', texte)
                for code, libelle in matches:
                    if len(code) >= 3: plan[code.strip()] = libelle.strip()
    return plan if plan else {"401": "Fournisseurs", "411": "Clients", "6281": "Entretien et réparations"}

st.sidebar.header("⚙️ Paramètres")
plan_file = st.sidebar.file_uploader("Uploader Plan SYSCOHADA PDF")
PLAN_COMPTABLE = charger_plan_comptable(plan_file)

def get_libelle_compte(code):
    return PLAN_COMPTABLE.get(code, "Compte non référencé")
st.sidebar.success(f"{len(PLAN_COMPTABLE)} comptes actifs")

# === 4. LE RESTE DE TON CODE EST PRESQUE IDENTIQUE ===
# === 2. CHARGER CGI ===
@st.cache_data
def charger_cgi(uploaded_file):
    texte_cgi = ""
    if uploaded_file:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages: texte_cgi += page.extract_text() + "\n"
        except: pass
    return texte_cgi if texte_cgi else "CGI non chargé"

cgi_file = st.sidebar.file_uploader("Uploader CGI 2026 PDF")
CGI_TEXTE = charger_cgi(cgi_file)

# === PARAMETRAGE ===
st.sidebar.header("📁 Paramétrage")
type_doc_choisi = st.sidebar.selectbox("Type de document", ["Facture d'achat", "Facture de vente", "Relevé bancaire"])
mapping_journal = {"Facture d'achat": "ACHAT", "Facture de vente": "VENTE", "Relevé bancaire": "BANQUE"}
journal_defaut = mapping_journal[type_doc_choisi]

# === BASE DE REGLES ===
EXONERATIONS_TVA = ["produit pharmaceutique", "livre", "produit agricole non transformé", "éducation", "santé", "exportation", "location immobilière habitation"]
TAUX_AIB = {"biens": 0.01, "travaux": 0.03, "prestation": 0.03, "prestation_intel": 0.05}
SEUIL_AIB = st.sidebar.checkbox("Appliquer seuil 10 000 FCFA", value=False)

def analyser_eligibilite(data):
    eligible_tva = "Oui"; eligible_aib = "Oui"; motif = []
    tva_montant = data.get("tva", 0); aib_montant = 0; taux_aib_applique = 0
    ht = data.get("ht", 0); libelle = data.get("libelle", "").lower(); nifu = data.get("nifu", "")
    if not nifu or nifu == "N/A": return "Non", "Non", "⚠️ Absence de N°IFU Art 227", 0, 0, 0.0
    if any(exo in libelle for exo in EXONERATIONS_TVA): eligible_tva = "Non"; motif.append(f"Exonéré TVA Art 229"); tva_montant = 0
    if SEUIL_AIB and ht < 10000 and eligible_aib == "Oui": eligible_aib = "Non"; motif.append("HT < 10 000 FCFA")
    if eligible_aib == "Oui": taux_aib_applique = TAUX_AIB.get(data.get("type_operation","biens"), 0.01); aib_montant = ht * taux_aib_applique
    if not motif: motif = ["Éligible"]
    return eligible_tva, eligible_aib, " | ".join(motif), tva_montant, aib_montant, taux_aib_applique*100

# Je te mets juste les 2 blocs qui changent : Traitement et Imputation

# === UPLOAD + TRAITEMENT ===
fichiers = st.file_uploader(f"Charge tes documents", type=["pdf", "png", "jpg"], accept_multiple_files=True)
if st.button("🚀 Lancer le traitement", type="primary"):
    if fichiers:
        resultats_detail = st.session_state.resultats_detail.copy()
        progress = st.progress(0)
        for i, fichier in enumerate(fichiers):
            file_bytes = fichier.read()
            prompt = """Extrait en JSON: {"n_facture": "", "date": "JJ/MM/AAAA", "fournisseur": "", "nifu": "", "libelle": "", "type_operation": "biens", "ht": 0, "tva": 0, "ttc": 0}"""
            response = model.generate_content([prompt, {"mime_type": fichier.type, "data": file_bytes}])
            try: data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
            except: data = {"n_facture": fichier.name, "libelle": "Erreur extraction"}
            #... ta fonction analyser_eligibilite ici...
            resultats_detail.append({"Type Doc": "Facture d'achat", "Journal": "ACHAT", "Fichier": fichier.name, "N° Pièce": data.get("n_facture"), "Date": data.get("date"), "Tiers": data.get("fournisseur"), "Libellé": data.get("libelle"), "N°IFU": data.get("nifu"), "HT": data.get("ht"), "TVA 18%": data.get("tva"), "AIB": 0, "Taux AIB": 0, "TTC": data.get("ttc")})
            progress.progress((i+1)/len(fichiers))
        st.session_state.resultats_detail = resultats_detail
        sauvegarder_dans_db()
        st.success(f"{len(fichiers)} documents traités et sauvegardés!")

if st.session_state.resultats_detail:
    df_detail = pd.DataFrame(st.session_state.resultats_detail)
    st.dataframe(df_detail, use_container_width=True, hide_index=True)

# === SECTION IMPUTATION ===
st.divider()
st.header("📒 Fiche d'Imputation Comptable")
if st.session_state.resultats_detail:
    df_a_imputer = pd.DataFrame(st.session_state.resultats_detail)
    piece_choisie = st.selectbox("1. Sélectionner un document", df_a_imputer["N° Pièce"].unique())
    details = df_a_imputer[df_a_imputer["N° Pièce"] == piece_choisie].iloc[0]

    col_c1, col_c2, col_c3, col_c4 = st.columns([2,3,2,2])
    with col_c1: m_compte = st.selectbox("N° de Compte", options=list(PLAN_COMPTABLE.keys()), format_func=lambda x: f"{x} - {get_libelle_compte(x)}")
    with col_c2: m_libelle = st.text_input("Libellé", value=details['Libellé'])
    with col_c3: sens_montant = st.radio("Sens", ["Débit", "Crédit"], horizontal=True)
    with col_c4: m_montant = st.number_input("Montant", value=float(details['TTC'] or 0.0))

    if st.button("➕ Ajouter la ligne"):
        st.session_state.imputations_epinglees.append({"Numéro Pièce": piece_choisie, "Date": details['Date'], "Journal": details['Journal'], "Compte": m_compte, "Libellé": m_libelle, "Débit": m_montant if sens_montant == "Débit" else 0.0, "Crédit": m_montant if sens_montant == "Crédit" else 0.0})
        sauvegarder_dans_db(); st.rerun()
    
    #... Colle ici ton code d'export Perfecto/SAI/Sage/Hypersoft...

    #... Colle ici ta section Declaration TVA DGI...

# === FONCTION EXPORT 4 LOGICIELS ===
    def formater_export(data, logiciel):
        df = pd.DataFrame(data)
        if df.empty: return ""
        mapping_journal_export = {"ACHAT": "ACH", "VENTE": "VTE", "BANQUE": "BQ"}
        df["Journal"] = df["Journal"].map(mapping_journal_export).fillna("OD")
        df["Date_dt"] = pd.to_datetime(df["Date"], errors='coerce')
        df["Compte"] = df["Compte"].astype(str).str.zfill(6)
        df["Libellé"] = df["Libellé"].astype(str)

        if logiciel == "Perfecto":
            def get_codes(row):
                code_tva = "T18" if row["TVA"] > 0 else "T00"
                code_aib = ""
                if row["AIB"] > 0:
                    if row["Taux AIB"] == 1: code_aib = "AIB1"
                    elif row["Taux AIB"] == 3: code_aib = "AIB3"
                    elif row["Taux AIB"] == 5: code_aib = "AIB5"
                return pd.Series([code_tva, code_aib])
            df[["CodeTVA", "CodeAIB"]] = df.apply(get_codes, axis=1)
            df_out = pd.DataFrame()
            df_out["Journal"] = df["Journal"]; df_out["Date"] = df["Date_dt"].dt.strftime('%d/%m/%Y')
            df_out["N°Pièce"] = df["Numéro Pièce"].str[:10]; df_out["Période"] = df["Date_dt"].dt.strftime('%m/%Y')
            df_out["Compte"] = df["Compte"]; df_out["Libellé"] = df["Libellé"].str[:35]
            df_out["Lettrage"] = ""; df_out["Débit"] = df["Débit"].round(2); df_out["Crédit"] = df["Crédit"].round(2)
            df_out["CodeTVA"] = df["CodeTVA"]; df_out["CodeAIB"] = df["CodeAIB"]
            return df_out.to_csv(sep=';', index=False, decimal='.')

        elif logiciel == "SAI":
            df_out = pd.DataFrame()
            df_out["Journal"] = df["Journal"]; df_out["Date"] = df["Date_dt"].dt.strftime('%d/%m/%Y')
            df_out["N°Pièce"] = df["Numéro Pièce"].str[:10]; df_out["Compte"] = df["Compte"]
            df_out["Libellé"] = df["Libellé"].str[:30]; df_out["Débit"] = df["Débit"].astype(int)
            df_out["Crédit"] = df["Crédit"].astype(int); df_out["Tiers"] = df["Compte"]; df_out["Echéance"] = ""
            return df_out.to_csv(sep=';', index=False)

        elif logiciel == "Sage":
            df_out = pd.DataFrame()
            df_out["Journal"] = df["Journal"]; df_out["Date"] = df["Date_dt"].dt.strftime('%d/%m/%Y')
            df_out["N°Pièce"] = df["Numéro Pièce"].str[:17]; df_out["Compte Général"] = df["Compte"]
            df_out["Compte Tiers"] = df["Compte"]; df_out["Libellé"] = df["Libellé"].str[:35]
            df_out["Débit"] = df["Débit"].round(2); df_out["Crédit"] = df["Crédit"].round(2)
            return df_out.to_csv(sep=';', index=False, decimal='.')

        elif logiciel == "Hypersoft":
            df_out = pd.DataFrame()
            df_out["Journal"] = df["Journal"]; df_out["Date"] = df["Date_dt"].dt.strftime('%Y%m%d')
            df_out["N°Pièce"] = df["Numéro Pièce"].str[:15]; df_out["Compte"] = df["Compte"]
            df_out["Libellé"] = df["Libellé"].str[:25]; df_out["Débit"] = df["Débit"].round(2)
            df_out["Crédit"] = df["Crédit"].round(2); df_out["Sens"] = df.apply(lambda x: "D" if x["Débit"]>0 else "C", axis=1)
            return df_out.to_csv(sep='|', index=False, decimal='.')
        return ""

    st.divider()
    st.subheader("📤 Export vers Logiciels Comptables")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📤 Perfecto"):
            data = formater_export(st.session_state.imputations_epinglees, "Perfecto")
            st.download_button("Télécharger", data, f"Perfecto_{datetime.now().strftime('%Y%m%d')}.txt")
    with col2:
        if st.button("📤 SAI"):
            data = formater_export(st.session_state.imputations_epinglees, "SAI")
            st.download_button("Télécharger", data, f"SAI_{datetime.now().strftime('%Y%m%d')}.txt")
    with col3:
        if st.button("📤 Sage"):
            data = formater_export(st.session_state.imputations_epinglees, "Sage")
            st.download_button("Télécharger", data, f"Sage_{datetime.now().strftime('%Y%m%d')}.csv")
    with col4:
        if st.button("📤 Hypersoft"):
            data = formater_export(st.session_state.imputations_epinglees, "Hypersoft")
            st.download_button("Télécharger", data, f"Hypersoft_{datetime.now().strftime('%Y%m%d')}.txt")

    # ZONE CONSEIL
    if st.session_state.ask_help_for:
        aide = st.session_state.ask_help_for
        with st.container(border=True):
            st.write(f"💡 **Conseil pour imputation**")
            prompt = f"Expert comptable SYSCOHADA Bénin. Facture Libellé='{aide['facture']['Libellé']}', HT={aide['facture']['HT']}. Quel(s) compte(s) 4 chiffres recommandes-tu? Base-toi sur le CGI 2026: {CGI_TEXTE[:4000]}. Cite l'article. Réponse courte."
            st.info(model.generate_content(prompt).text)
            if st.button("Fermer le conseil"): st.session_state.ask_help_for = None; st.rerun()

# === SECTION DECLARATION TVA DGI ===
st.divider()
st.header("📊 Déclaration TVA & AIB - DGI SFE")

if st.session_state.resultats_detail:
    df_docs = pd.DataFrame(st.session_state.resultats_detail)
    df_docs["Date_dt"] = pd.to_datetime(df_docs["Date"], errors='coerce')

    col_p1, col_p2 = st.columns(2)
    with col_p1: mois = st.selectbox("Mois", range(1,13), format_func=lambda x: datetime(2026, x, 1).strftime('%B'))
    with col_p2: annee = st.selectbox("Année", [2025, 2026, 2027])

    df_mois = df_docs[(df_docs["Date_dt"].dt.month == mois) & (df_docs["Date_dt"].dt.year == annee)]

    if not df_mois.empty:
        st.subheader(f"Récapitulatif {datetime(2026, mois, 1).strftime('%B %Y')}")

        ca_vente_ht = df_mois[df_mois["Type Doc"]=="Facture de vente"]["HT"].sum()
        tva_collectee = df_mois[df_mois["Type Doc"]=="Facture de vente"]["TVA 18%"].sum()
        achat_ht = df_mois[df_mois["Type Doc"]=="Facture d'achat"]["HT"].sum()
        tva_deductible = df_mois[df_mois["Type Doc"]=="Facture d'achat"]["TVA 18%"].sum()
        aib_collecte = df_mois[df_mois["Type Doc"]=="Facture d'achat"]["AIB"].sum()

        tva_a_payer = tva_collectee - tva_deductible
        credit_tva = abs(tva_a_payer) if tva_a_payer < 0 else 0
        tva_a_payer = max(0, tva_a_payer)

        data_recap = {
            "LIBELLE": ["CHIFFRE D'AFFAIRES HT", "TVA COLLECTEE 18%", "ACHATS HT", "TVA DEDUCTIBLE 18%", "TVA NETTE A PAYER", "CREDIT DE TVA", "AIB COLLECTEE"],
            "MONTANT (FCFA)": [ca_vente_ht, tva_collectee, achat_ht, tva_deductible, tva_a_payer, credit_tva, aib_collecte]
        }
        df_recap = pd.DataFrame(data_recap)
        st.dataframe(df_recap, use_container_width=True, hide_index=True)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("TVA à Payer", f"{tva_a_payer:,.0f} FCFA")
        col_m2.metric("Crédit TVA", f"{credit_tva:,.0f} FCFA")
        col_m3.metric("AIB à Verser", f"{aib_collecte:,.0f} FCFA")

        def generer_csv_sfe(df_recap, mois, annee):
            output = io.StringIO()
            output.write(f"PERIODE;{mois:02d}/{annee}\n")
            output.write(f"RAISON SOCIALE;MON CABINET ONE7\n") # A MODIFIER
            output.write(f"NIFU;0000\n") # A MODIFIER
            output.write("\nLIBELLE;MONTANT\n")
            for index, row in df_recap.iterrows():
                output.write(f"{row['LIBELLE']};{row['MONTANT (FCFA)']:.0f}\n")
            return output.getvalue()

        csv_sfe = generer_csv_sfe(df_recap, mois, annee)
        st.download_button(label="📥 Télécharger Déclaration SFE pour DGI", data=csv_sfe, file_name=f"DECL_TVA_{annee}{mois:02d}.csv", mime="text/csv")
        st.info("Importez ce fichier sur https://www.impots.bj > Espace SFE")
    else:
        st.warning("Aucun document trouvé pour cette période")
else:
    st.warning("Traitez d'abord des documents pour générer la déclaration")

# === ASSISTANT GENERAL ===
st.divider()
st.header("💬 Assistant Fiscal One7")
question = st.text_input("Posez votre question sur la fiscalité béninoise ou le SYSCOHADA...")
if question:
    try :
        prompt = f"Tu es un expert fiscal au Bénin. Réponds UNIQUEMENT en te basant sur le Code Général des Impôts 2026 et le SYSCOHADA. Cite l'article exact. Si pas dans le texte, dis-le. Question: {question} \n\n TEXTE DE REFERENCE: {CGI_TEXTE[:8000]}"
        st.info(model.generate_content(prompt).text)
    # === DECONNEXION AUTO SI TOKEN EXPIRE ===
    except Exception as e:
        if "JWT" in str(e):
            st.warning("Session expirée. Reconnectez-vous.")
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
        else:
            st.error(f"Erreur IA: {e}")

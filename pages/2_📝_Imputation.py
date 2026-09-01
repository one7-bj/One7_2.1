import streamlit as st
import pandas as pd, re, pdfplumber
from supabase import create_client

st.header("📒 Fiche d'Imputation Comptable")

user_id = st.session_state.user.id
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Charger données
def charger_depuis_db():
    res = supabase.table('documents').select("*").eq('user_id', user_id).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df.rename(columns={
            'n_piece': 'N° Pièce', 'date': 'date_doc', 'journal': 'Journal',
            'tiers': 'Fournisseur', 'libelle': 'Libellé', 'type_doc': 'TYPE_DOC',
            'ht': 'HT', 'tva': 'TVA', 'aib': 'AIB', 'ttc': 'TTC', 'taux_aib': 'TAUX_AIB'
        }, inplace=True)
        return df
    return pd.DataFrame()

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

plan_file = st.sidebar.file_uploader("Uploader Plan SYSCOHADA PDF")
PLAN_COMPTABLE = charger_plan_comptable(plan_file)
def get_libelle_compte(code): return PLAN_COMPTABLE.get(code, "Compte non référencé")
st.sidebar.success(f"{len(PLAN_COMPTABLE)} comptes actifs")

df_a_imputer = charger_depuis_db()
if not df_a_imputer.empty:
    piece_choisie = st.selectbox("1. Sélectionner un document", df_a_imputer["N° Pièce"].unique())
    details = df_a_imputer[df_a_imputer["N° Pièce"] == piece_choisie].iloc[0]

    col_c1, col_c2, col_c3, col_c4 = st.columns([2,3,2,2])
    with col_c1: m_compte = st.selectbox("N° de Compte", options=list(PLAN_COMPTABLE.keys()), format_func=lambda x: f"{x} - {get_libelle_compte(x)}")
    with col_c2: m_libelle = st.text_input("Libellé", value=str(details.get('Libellé', '')))
    with col_c3: sens_montant = st.radio("Sens", ["Débit", "Crédit"], horizontal=True)
    with col_c4: m_montant = st.number_input("Montant", value=float(details['TTC'] or 0.0))

    if st.button("➕ Ajouter la ligne"):
        if 'imputations_epinglees' not in st.session_state: st.session_state.imputations_epinglees = []
        st.session_state.imputations_epinglees.append({
            "Numéro Pièce": piece_choisie,
            "Date": details['date_doc'], "Journal": details['Journal'], "Fournisseur": details['Fournisseur'],
            "Compte": m_compte, "Libellé": m_libelle,
            "Débit": m_montant if sens_montant == "Débit" else 0.0,
            "Crédit": m_montant if sens_montant == "Crédit" else 0.0
        })
        # Sauvegarde imputation
        df_imp = pd.DataFrame(st.session_state.imputations_epinglees)
        df_imp['user_id'] = user_id
        df_imp = df_imp.rename(columns={"Numéro Pièce": "n_piece", "Compte": "compte", "Débit": "debit", "Crédit": "credit"})
        supabase.table('imputations').upsert(df_imp.to_dict('records'), on_conflict='user_id,n_piece,compte').execute()
        st.rerun()

    if st.session_state.get('imputations_epinglees'):
        st.subheader("Lignes imputées épinglées")
        st.dataframe(pd.DataFrame(st.session_state.imputations_epinglees), use_container_width=True, hide_index=True)
else:
    st.warning("Aucun document à imputer. Va d'abord dans l'onglet Import.")

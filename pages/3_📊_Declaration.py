import streamlit as st
import pandas as pd, io
from datetime import datetime
from supabase import create_client

st.header("📊 Déclaration TVA & AIB - DGI SFE")

user_id = st.session_state.user.id
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def charger_depuis_db():
    res = supabase.table('documents').select("*").eq('user_id', user_id).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df.rename(columns={'n_piece': 'N° Pièce', 'date': 'date_doc', 'journal': 'Journal', 'tiers': 'Fournisseur', 'libelle': 'Libellé', 'type_doc': 'TYPE_DOC', 'ht': 'HT', 'tva': 'TVA', 'aib': 'AIB', 'ttc': 'TTC'}, inplace=True)
        return df
    return pd.DataFrame()

df_docs = charger_depuis_db()
if not df_docs.empty:
    df_docs["Date_dt"] = pd.to_datetime(df_docs["date_doc"], errors='coerce')
    df_docs = df_docs.dropna(subset=['Date_dt'])

    col_p1, col_p2 = st.columns(2)
    with col_p1: mois = st.selectbox("Mois", range(1,13), format_func=lambda x: datetime(2026, x, 1).strftime('%B'))
    with col_p2: annee = st.selectbox("Année", [2025, 2026, 2027])

    df_mois = df_docs[(df_docs["Date_dt"].dt.month == mois) & (df_docs["Date_dt"].dt.year == annee)]

    st.subheader(f"Récapitulatif {datetime(2026, mois, 1).strftime('%B %Y')}")
    ca_vente_ht = df_mois[df_mois["TYPE_DOC"]=="Facture de vente"]["HT"].sum()
    tva_collectee = df_mois[df_mois["TYPE_DOC"]=="Facture de vente"]["TVA"].sum()
    achat_ht = df_mois[df_mois["TYPE_DOC"]=="Facture d'achat"]["HT"].sum()
    tva_deductible = df_mois[df_mois["TYPE_DOC"]=="Facture d'achat"]["TVA"].sum()
    aib_collecte = df_mois[df_mois["TYPE_DOC"]=="Facture d'achat"]["AIB"].sum()

    tva_a_payer = tva_collectee - tva_deductible
    credit_tva = abs(tva_a_payer) if tva_a_payer < 0 else 0
    tva_a_payer = max(0, tva_a_payer)

    data_recap = {"LIBELLE": ["CHIFFRE D'AFFAIRES HT", "TVA COLLECTEE 18%", "ACHATS HT", "TVA DEDUCTIBLE 18%", "TVA NETTE A PAYER", "CREDIT DE TVA", "AIB COLLECTEE"], "MONTANT (FCFA)": [ca_vente_ht, tva_collectee, achat_ht, tva_deductible, tva_a_payer, credit_tva, aib_collecte]}
    df_recap = pd.DataFrame(data_recap)
    st.dataframe(df_recap, use_container_width=True, hide_index=True)

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("TVA à Payer", f"{tva_a_payer:,.0f} FCFA")
    col_m2.metric("Crédit TVA", f"{credit_tva:,.0f} FCFA")
    col_m3.metric("AIB à Verser", f"{aib_collecte:,.0f} FCFA")

    csv_sfe = "PERIODE;" + f"{mois:02d}/{annee}\n" + df_recap.to_csv(sep=';', index=False)
    st.download_button(label="📥 Télécharger Déclaration SFE pour DGI", data=csv_sfe, file_name=f"DECL_TVA_{annee}{mois:02d}.csv", mime="text/csv")
else:
    st.warning("Aucun document trouvé. Importe d'abord des factures.")

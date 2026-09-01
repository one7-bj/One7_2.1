import streamlit as st
import pandas as pd, pdfplumber, re
from supabase import create_client

st.header("⚙️ Paramètres & Assistant Fiscal")

user_id = st.session_state.user.id
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# CGI
cgi_file = st.file_uploader("Uploader CGI 2026 PDF")
if cgi_file:
    texte_cgi = ""
    with pdfplumber.open(cgi_file) as pdf:
        for page in pdf.pages: texte_cgi += page.extract_text() + "\n"
    st.session_state.cgi_texte = texte_cgi
    supabase.table('parametres_generaux').upsert({'user_id': user_id, 'cgi_texte': texte_cgi}).execute()
    st.success("CGI chargé et sauvegardé")

# Assistant
st.divider()
st.subheader("💬 Assistant Fiscal One7")
question = st.text_input("Posez votre question sur la fiscalité béninoise...")

if question and st.button("Poser la question"):
    if 'cgi_texte' in st.session_state:
        contexte = f"Contexte CGI Bénin: {st.session_state.cgi_texte[:4000]}"
        prompt = f"{contexte}\n\nQuestion: {question}\nRéponds uniquement sur la fiscalité du Bénin."
        st.write("Réponse de l'IA:...")
    else:
        st.warning("Upload d'abord le CGI 2026")

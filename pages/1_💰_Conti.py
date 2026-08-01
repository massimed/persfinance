import streamlit as st
import pandas as pd
from db import init_db, get_accounts, add_account, delete_account

init_db()
st.set_page_config(page_title="Conti", page_icon="💰", layout="wide")
st.title("💰 Conti")

with st.expander("➕ Aggiungi nuovo conto"):
    with st.form("nuovo_conto"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Nome conto (es. SRBank, BancoPosta)")
        currency = c2.selectbox("Valuta", ["NOK", "EUR"])
        balance = c3.number_input("Saldo iniziale", step=100.0, format="%.2f")
        account_type = c4.selectbox("Tipo", ["corrente", "risparmio", "carta di credito", "contanti"])
        submitted = st.form_submit_button("Aggiungi conto")
        if submitted:
            if not name.strip():
                st.error("Inserisci un nome per il conto.")
            else:
                add_account(name.strip(), currency, balance, account_type)
                st.success(f"Conto '{name}' aggiunto.")
                st.rerun()

st.divider()

accounts = get_accounts()
if not accounts:
    st.info("Nessun conto presente.")
else:
    df = pd.DataFrame([dict(a) for a in accounts])
    for _, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
        c1.write(f"**{row['name']}**")
        c2.write(row["account_type"])
        c3.write(row["currency"])
        c4.write(f"{row['balance']:,.2f}")
        if c5.button("🗑️", key=f"del_{row['id']}"):
            delete_account(row["id"])
            st.rerun()

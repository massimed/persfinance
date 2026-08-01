import streamlit as st
import pandas as pd
from datetime import date
from db import init_db, get_budgets, upsert_budget, delete_budget, spent_in_category

init_db()
st.set_page_config(page_title="Budget", page_icon="📊", layout="wide")
st.title("📊 Budget mensile")

CATEGORIE = [
    "Spesa alimentare", "Bollette", "Trasporti", "Salute", "Svago",
    "Ristoranti", "Casa", "Tasse", "Altro",
]

c1, c2 = st.columns(2)
mese = c1.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1, format_func=lambda m: f"{m:02d}")
anno = c2.number_input("Anno", value=date.today().year, step=1)

with st.expander("➕ Imposta / aggiorna budget"):
    with st.form("nuovo_budget"):
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Categoria", CATEGORIE)
        amount_limit = c2.number_input("Limite", min_value=0.0, step=50.0, format="%.2f")
        currency = c3.selectbox("Valuta", ["NOK", "EUR"])
        if st.form_submit_button("Salva budget"):
            upsert_budget(category, mese, anno, amount_limit, currency)
            st.success("Budget salvato.")
            st.rerun()

st.divider()

budgets = get_budgets(mese, anno)
if not budgets:
    st.info("Nessun budget impostato per questo mese.")
else:
    for b in budgets:
        speso = spent_in_category(b["category"], mese, anno)
        perc = min(speso / b["amount_limit"], 1.0) if b["amount_limit"] > 0 else 0

        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{b['category']}** — {speso:,.2f} / {b['amount_limit']:,.2f} {b['currency']}")
            st.progress(perc)
            if speso > b["amount_limit"]:
                st.error("Budget superato!")
        if c2.button("🗑️", key=f"delb_{b['id']}"):
            delete_budget(b["id"])
            st.rerun()

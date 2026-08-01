import streamlit as st
import pandas as pd
from datetime import date
from db import init_db, get_accounts, get_transactions, add_transaction, delete_transaction

init_db()
st.set_page_config(page_title="Transazioni", page_icon="💸", layout="wide")
st.title("💸 Transazioni")

accounts = get_accounts()
if not accounts:
    st.warning("Crea prima almeno un conto nella pagina Conti.")
    st.stop()

acc_options = {f"{a['name']} ({a['currency']})": a["id"] for a in accounts}

CATEGORIE = [
    "Stipendio", "Affitto ricevuto", "Spesa alimentare", "Bollette", "Trasporti",
    "Salute", "Svago", "Ristoranti", "Casa", "Tasse", "Investimenti", "Altro",
]

with st.expander("➕ Nuova transazione", expanded=True):
    with st.form("nuova_tx", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        acc_label = c1.selectbox("Conto", list(acc_options.keys()))
        tx_type = c2.selectbox("Tipo", ["uscita", "entrata"])
        tx_date = c3.date_input("Data", value=date.today())

        c4, c5, c6 = st.columns(3)
        amount = c4.number_input("Importo", min_value=0.0, step=10.0, format="%.2f")
        currency = c5.selectbox("Valuta transazione", ["NOK", "EUR"])
        category = c6.selectbox("Categoria", CATEGORIE)

        description = st.text_input("Descrizione")
        submitted = st.form_submit_button("Registra transazione")

        if submitted:
            if amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            else:
                account_id = acc_options[acc_label]
                add_transaction(account_id, tx_date.isoformat(), description, category, amount, currency, tx_type)
                st.success("Transazione registrata.")
                st.rerun()

st.divider()

st.subheader("Storico")

c1, c2 = st.columns(2)
filtro_conto = c1.selectbox("Filtra per conto", ["Tutti"] + list(acc_options.keys()))
filtro_categoria = c2.selectbox("Filtra per categoria", ["Tutte"] + CATEGORIE)

tx = get_transactions()
if tx:
    df = pd.DataFrame([dict(t) for t in tx])
    if filtro_conto != "Tutti":
        df = df[df["account_id"] == acc_options[filtro_conto]]
    if filtro_categoria != "Tutte":
        df = df[df["category"] == filtro_categoria]

    for _, row in df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1.2, 2, 2, 1.5, 1.5, 0.6])
        c1.write(row["date"])
        c2.write(row["account_name"])
        c3.write(row["description"] or "—")
        c4.write(row["category"] or "—")
        segno = "+" if row["tx_type"] == "entrata" else "-"
        colore = "green" if row["tx_type"] == "entrata" else "red"
        c5.markdown(f":{colore}[{segno}{row['amount']:,.2f} {row['currency']}]")
        if c6.button("🗑️", key=f"deltx_{row['id']}"):
            delete_transaction(row["id"])
            st.rerun()

    st.caption(f"{len(df)} transazioni mostrate")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Esporta CSV", csv, "transazioni.csv", "text/csv")
else:
    st.info("Nessuna transazione registrata.")

import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

from db import (
    init_db, get_accounts, get_transactions, process_due_recurring,
    convert, execute, is_remote,
)

st.set_page_config(page_title="Gestione Finanze", page_icon="💰", layout="wide")

init_db()
process_due_recurring()

st.title("💰 Gestione Finanze")
st.caption("Dashboard multi-valuta NOK / EUR")
if is_remote():
    st.caption("🟢 Database: Turso (dati persistenti)")
else:
    st.caption("🟡 Database: locale (i dati non sopravvivono ai riavvii su Streamlit Cloud — vedi README)")

accounts = get_accounts()

if not accounts:
    st.info("Nessun conto configurato. Vai alla pagina **Conti** dal menu laterale per aggiungerne uno.")
    st.stop()

# ---------- Riepilogo saldi convertiti ----------
valuta_base = st.selectbox("Valuta di riepilogo", ["NOK", "EUR"], index=0)

df_acc = pd.DataFrame([dict(a) for a in accounts])
df_acc["saldo_convertito"] = df_acc.apply(
    lambda r: convert(r["balance"], r["currency"], valuta_base), axis=1
)

totale = df_acc["saldo_convertito"].sum()

col1, col2, col3 = st.columns(3)
col1.metric(f"Patrimonio totale ({valuta_base})", f"{totale:,.2f}")
col2.metric("Conti attivi", len(df_acc))

mese_corrente = date.today().strftime("%Y-%m")
entrate_mese = execute(
    """SELECT COALESCE(SUM(amount),0) AS t FROM transactions
       WHERE tx_type='entrata' AND strftime('%Y-%m', date) = ?""",
    [mese_corrente],
).rows[0][0]
uscite_mese = execute(
    """SELECT COALESCE(SUM(amount),0) AS t FROM transactions
       WHERE tx_type='uscita' AND strftime('%Y-%m', date) = ?""",
    [mese_corrente],
).rows[0][0]
col3.metric("Bilancio mese corrente", f"{entrate_mese - uscite_mese:,.2f}")

st.divider()

# ---------- Saldi per conto ----------
st.subheader("Saldi per conto")
st.dataframe(
    df_acc[["name", "account_type", "currency", "balance", "saldo_convertito"]]
    .rename(columns={
        "name": "Conto", "account_type": "Tipo", "currency": "Valuta",
        "balance": "Saldo", "saldo_convertito": f"Saldo in {valuta_base}",
    }),
    use_container_width=True, hide_index=True,
)

chart = alt.Chart(df_acc).mark_bar().encode(
    x=alt.X("name:N", title="Conto"),
    y=alt.Y("saldo_convertito:Q", title=f"Saldo ({valuta_base})"),
    color="currency:N",
    tooltip=["name", "balance", "currency", "saldo_convertito"],
)
st.altair_chart(chart, use_container_width=True)

st.divider()

# ---------- Ultime transazioni ----------
st.subheader("Ultime transazioni")
tx = get_transactions(limit=15)
if tx:
    df_tx = pd.DataFrame([dict(t) for t in tx])
    df_tx = df_tx[["date", "account_name", "description", "category", "amount", "currency", "tx_type"]]
    df_tx.columns = ["Data", "Conto", "Descrizione", "Categoria", "Importo", "Valuta", "Tipo"]
    st.dataframe(df_tx, use_container_width=True, hide_index=True)
else:
    st.write("Nessuna transazione registrata.")

st.divider()

# ---------- Andamento entrate/uscite ultimi 6 mesi ----------
st.subheader("Andamento ultimi 6 mesi")
rows = execute(
    """SELECT strftime('%Y-%m', date) AS mese, tx_type,
              SUM(amount) AS totale
       FROM transactions
       WHERE date >= date('now', '-6 months')
       GROUP BY mese, tx_type
       ORDER BY mese"""
)
rows = [dict(zip(rows.columns, r)) for r in rows.rows]

if rows:
    df_trend = pd.DataFrame(rows)
    trend_chart = alt.Chart(df_trend).mark_line(point=True).encode(
        x="mese:N", y="totale:Q", color="tx_type:N",
        tooltip=["mese", "tx_type", "totale"],
    )
    st.altair_chart(trend_chart, use_container_width=True)
else:
    st.write("Dati insufficienti per il grafico.")

st.sidebar.success("Usa il menu qui sopra per navigare tra Conti, Transazioni, Budget, Ricorrenti e Obiettivi.")

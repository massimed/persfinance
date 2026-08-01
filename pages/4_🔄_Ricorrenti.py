import streamlit as st
import pandas as pd
from datetime import date
from db import init_db, get_accounts, get_recurring, add_recurring, toggle_recurring, delete_recurring

init_db()
st.set_page_config(page_title="Ricorrenti", page_icon="🔄", layout="wide")
st.title("🔄 Transazioni ricorrenti")
st.caption("Vengono generate automaticamente quando apri l'app e la data è scaduta (es. affitto, stipendio, abbonamenti).")

accounts = get_accounts()
if not accounts:
    st.warning("Crea prima almeno un conto nella pagina Conti.")
    st.stop()

acc_options = {f"{a['name']} ({a['currency']})": a["id"] for a in accounts}

with st.expander("➕ Nuova ricorrenza", expanded=True):
    with st.form("nuova_ricorrenza", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        description = c1.text_input("Descrizione (es. Affitto, Stipendio)")
        acc_label = c2.selectbox("Conto", list(acc_options.keys()))
        tx_type = c3.selectbox("Tipo", ["uscita", "entrata"])

        c4, c5, c6 = st.columns(3)
        amount = c4.number_input("Importo", min_value=0.0, step=10.0, format="%.2f")
        currency = c5.selectbox("Valuta", ["NOK", "EUR"])
        frequency = c6.selectbox("Frequenza", ["mensile", "settimanale", "annuale"])

        c7, c8 = st.columns(2)
        category = c7.text_input("Categoria", value="Altro")
        next_date = c8.date_input("Prossima esecuzione", value=date.today())

        if st.form_submit_button("Aggiungi ricorrenza"):
            if not description.strip() or amount <= 0:
                st.error("Compila descrizione e importo.")
            else:
                add_recurring(
                    description.strip(), category, amount, currency,
                    acc_options[acc_label], tx_type, frequency, next_date.isoformat(),
                )
                st.success("Ricorrenza aggiunta.")
                st.rerun()

st.divider()

recs = get_recurring()
if not recs:
    st.info("Nessuna transazione ricorrente configurata.")
else:
    for r in recs:
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1.3, 1.3, 1, 1])
        c1.write(f"**{r['description']}** ({r['account_name']})")
        segno = "+" if r["tx_type"] == "entrata" else "-"
        c2.write(f"{segno}{r['amount']:,.2f} {r['currency']}")
        c3.write(r["frequency"])
        c4.write(f"Prossima: {r['next_date']}")
        attivo = c5.toggle("Attiva", value=bool(r["active"]), key=f"tog_{r['id']}")
        if attivo != bool(r["active"]):
            toggle_recurring(r["id"], attivo)
            st.rerun()
        if c6.button("🗑️", key=f"delr_{r['id']}"):
            delete_recurring(r["id"])
            st.rerun()

import streamlit as st
from datetime import date
from db import init_db, get_goals, add_goal, contribute_to_goal, delete_goal

init_db()
st.set_page_config(page_title="Obiettivi", page_icon="🐷", layout="wide")
st.title("🐷 Obiettivi di risparmio")

with st.expander("➕ Nuovo obiettivo"):
    with st.form("nuovo_obiettivo", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Nome obiettivo (es. Vacanza, Fondo emergenza)")
        target = c2.number_input("Importo target", min_value=0.0, step=100.0, format="%.2f")
        currency = c3.selectbox("Valuta", ["NOK", "EUR"])
        deadline = c4.date_input("Scadenza", value=date.today())
        if st.form_submit_button("Crea obiettivo"):
            if not name.strip() or target <= 0:
                st.error("Inserisci nome e importo target validi.")
            else:
                add_goal(name.strip(), target, currency, deadline.isoformat())
                st.success("Obiettivo creato.")
                st.rerun()

st.divider()

goals = get_goals()
if not goals:
    st.info("Nessun obiettivo impostato.")
else:
    for g in goals:
        perc = min(g["current_amount"] / g["target_amount"], 1.0) if g["target_amount"] > 0 else 0
        st.subheader(g["name"])
        st.progress(perc)
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"{g['current_amount']:,.2f} / {g['target_amount']:,.2f} {g['currency']}")
        c2.write(f"Scadenza: {g['deadline']}")
        contrib = c3.number_input("Aggiungi importo", min_value=0.0, step=50.0, format="%.2f", key=f"contrib_{g['id']}")
        if c3.button("Versa", key=f"versa_{g['id']}"):
            if contrib > 0:
                contribute_to_goal(g["id"], contrib)
                st.rerun()
        if c4.button("🗑️", key=f"delg_{g['id']}"):
            delete_goal(g["id"])
            st.rerun()
        st.divider()

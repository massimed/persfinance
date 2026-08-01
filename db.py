"""
db.py — Livello dati per l'app di Gestione Finanze (versione Streamlit)

Usa Turso (libSQL, compatibile SQLite) come database esterno duraturo e gratuito.
Se non è configurato alcun database Turso (nessun secret impostato), l'app
funziona comunque in locale su un file SQLite, così puoi sviluppare e testare
senza account. Su Streamlit Cloud, configurando i secrets TURSO_DATABASE_URL
e TURSO_AUTH_TOKEN, i dati diventano persistenti tra un riavvio e l'altro.
"""

import os
from datetime import date
import requests
import streamlit as st
import libsql_client

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "finance.db")


def _get_secret(key):
    """Legge un secret in modo sicuro: restituisce None se il file secrets.toml
    non esiste o la chiave non è presente, invece di sollevare un'eccezione."""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def _turso_configured() -> bool:
    return bool(_get_secret("TURSO_DATABASE_URL")) and bool(_get_secret("TURSO_AUTH_TOKEN"))


@st.cache_resource(show_spinner=False)
def get_client():
    """Client libSQL, riutilizzato tra i rerun di Streamlit (connessione persistente)."""
    if _turso_configured():
        return libsql_client.create_client_sync(
            url=_get_secret("TURSO_DATABASE_URL"),
            auth_token=_get_secret("TURSO_AUTH_TOKEN"),
        )
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return libsql_client.create_client_sync(f"file:{DB_PATH}")


def is_remote() -> bool:
    return _turso_configured()


def _rows(result_set):
    """Converte un ResultSet libSQL in una lista di dict, per compatibilità con il resto dell'app."""
    cols = result_set.columns
    return [dict(zip(cols, row)) for row in result_set.rows]


def execute(sql, args=None):
    return get_client().execute(sql, args or [])


# ---------- INIZIALIZZAZIONE SCHEMA ----------

def init_db():
    execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            currency TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            account_type TEXT DEFAULT 'corrente',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            amount_limit REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'NOK',
            UNIQUE(category, month, year)
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS recurring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            tx_type TEXT NOT NULL,
            frequency TEXT NOT NULL,
            next_date TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'NOK',
            deadline TEXT
        )
    """)


# ---------- CAMBIO VALUTA ----------

@st.cache_data(ttl=3600, show_spinner=False)
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Tasso di cambio in tempo reale via Frankfurter API, con fallback."""
    if from_currency == to_currency:
        return 1.0
    try:
        r = requests.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"base": from_currency, "symbols": to_currency},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()["rates"][to_currency]
    except Exception:
        fallback = {("EUR", "NOK"): 11.7, ("NOK", "EUR"): 1 / 11.7}
        return fallback.get((from_currency, to_currency), 1.0)


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    return amount * get_exchange_rate(from_currency, to_currency)


# ---------- ACCOUNTS ----------

def get_accounts():
    return _rows(execute("SELECT * FROM accounts ORDER BY name"))


def add_account(name, currency, balance, account_type):
    execute(
        "INSERT INTO accounts (name, currency, balance, account_type) VALUES (?, ?, ?, ?)",
        [name, currency, balance, account_type],
    )


def update_account_balance(account_id, delta):
    execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", [delta, account_id])


def delete_account(account_id):
    # Niente FK cascade lato server (dipende dal supporto PRAGMA su stream remoto):
    # cancelliamo esplicitamente i record collegati per sicurezza.
    execute("DELETE FROM transactions WHERE account_id = ?", [account_id])
    execute("DELETE FROM recurring WHERE account_id = ?", [account_id])
    execute("DELETE FROM accounts WHERE id = ?", [account_id])


# ---------- TRANSACTIONS ----------

def get_transactions(limit=None):
    q = """
        SELECT t.*, a.name AS account_name, a.currency AS account_currency
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        ORDER BY t.date DESC, t.id DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    return _rows(execute(q))


def add_transaction(account_id, tx_date, description, category, amount, currency, tx_type):
    execute(
        """INSERT INTO transactions (account_id, date, description, category, amount, currency, tx_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [account_id, tx_date, description, category, amount, currency, tx_type],
    )

    acc_rows = _rows(execute("SELECT currency FROM accounts WHERE id = ?", [account_id]))
    if acc_rows:
        acc_currency = acc_rows[0]["currency"]
        converted = convert(amount, currency, acc_currency) if currency != acc_currency else amount
        delta = converted if tx_type == "entrata" else -converted
        update_account_balance(account_id, delta)


def delete_transaction(tx_id):
    tx_rows = _rows(execute("SELECT * FROM transactions WHERE id = ?", [tx_id]))
    if tx_rows:
        tx = tx_rows[0]
        acc_rows = _rows(execute("SELECT currency FROM accounts WHERE id = ?", [tx["account_id"]]))
        if acc_rows:
            acc_currency = acc_rows[0]["currency"]
            converted = (
                convert(tx["amount"], tx["currency"], acc_currency)
                if tx["currency"] != acc_currency else tx["amount"]
            )
            delta = -converted if tx["tx_type"] == "entrata" else converted
            execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", [delta, tx["account_id"]])
        execute("DELETE FROM transactions WHERE id = ?", [tx_id])


# ---------- BUDGETS ----------

def get_budgets(month, year):
    return _rows(execute(
        "SELECT * FROM budgets WHERE month = ? AND year = ? ORDER BY category", [month, year]
    ))


def upsert_budget(category, month, year, amount_limit, currency):
    execute(
        """INSERT INTO budgets (category, month, year, amount_limit, currency)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(category, month, year) DO UPDATE SET amount_limit = excluded.amount_limit""",
        [category, month, year, amount_limit, currency],
    )


def delete_budget(budget_id):
    execute("DELETE FROM budgets WHERE id = ?", [budget_id])


def spent_in_category(category, month, year):
    rows = _rows(execute(
        """SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
           WHERE category = ? AND tx_type = 'uscita'
           AND strftime('%m', date) = ? AND strftime('%Y', date) = ?""",
        [category, f"{month:02d}", str(year)],
    ))
    return rows[0]["total"] if rows else 0


# ---------- RECURRING ----------

def get_recurring(active_only=False):
    q = """SELECT r.*, a.name AS account_name FROM recurring r
           JOIN accounts a ON a.id = r.account_id"""
    if active_only:
        q += " WHERE r.active = 1"
    q += " ORDER BY r.next_date"
    return _rows(execute(q))


def add_recurring(description, category, amount, currency, account_id, tx_type, frequency, next_date):
    execute(
        """INSERT INTO recurring (description, category, amount, currency, account_id, tx_type, frequency, next_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [description, category, amount, currency, account_id, tx_type, frequency, next_date],
    )


def toggle_recurring(rec_id, active):
    execute("UPDATE recurring SET active = ? WHERE id = ?", [int(active), rec_id])


def delete_recurring(rec_id):
    execute("DELETE FROM recurring WHERE id = ?", [rec_id])


def _advance_date(d: date, frequency: str) -> date:
    if frequency == "settimanale":
        from datetime import timedelta
        return d + timedelta(days=7)
    if frequency == "annuale":
        try:
            return d.replace(year=d.year + 1)
        except ValueError:
            return d.replace(year=d.year + 1, day=28)
    month = d.month + 1
    year = d.year + (1 if month > 12 else 0)
    month = 1 if month > 12 else month
    day = min(d.day, 28)
    return d.replace(year=year, month=month, day=day)


def process_due_recurring():
    """Genera automaticamente le transazioni ricorrenti scadute (eseguito ad ogni avvio)."""
    today = date.today()
    due = _rows(execute(
        "SELECT * FROM recurring WHERE active = 1 AND date(next_date) <= date(?)",
        [today.isoformat()],
    ))
    for r in due:
        add_transaction(
            r["account_id"], r["next_date"], r["description"], r["category"],
            r["amount"], r["currency"], r["tx_type"],
        )
        next_d = _advance_date(date.fromisoformat(r["next_date"]), r["frequency"])
        execute("UPDATE recurring SET next_date = ? WHERE id = ?", [next_d.isoformat(), r["id"]])


# ---------- GOALS (SALVADANAIO) ----------

def get_goals():
    return _rows(execute("SELECT * FROM goals ORDER BY deadline"))


def add_goal(name, target_amount, currency, deadline):
    execute(
        "INSERT INTO goals (name, target_amount, currency, deadline) VALUES (?, ?, ?, ?)",
        [name, target_amount, currency, deadline],
    )


def contribute_to_goal(goal_id, amount):
    execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", [amount, goal_id])


def delete_goal(goal_id):
    execute("DELETE FROM goals WHERE id = ?", [goal_id])

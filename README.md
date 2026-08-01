# Gestione Finanze — Streamlit + Turso

Versione Streamlit dell'app di gestione finanze personali (equivalente della versione Flask/Docker su porta 8687), con **database esterno gratuito e duraturo (Turso)** così i dati sopravvivono ai riavvii su Streamlit Community Cloud.

## Funzionalità
- Conti multipli in NOK / EUR con saldo aggiornato automaticamente
- Transazioni (entrate/uscite) con conversione valuta in tempo reale (Frankfurter API)
- Budget mensili per categoria con barra di avanzamento
- Transazioni ricorrenti (affitto, stipendio, abbonamenti) generate automaticamente
- Obiettivi di risparmio ("salvadanaio") con percentuale di completamento
- Dashboard con patrimonio totale convertito, grafici andamento e saldi per conto
- Esportazione transazioni in CSV
- **Dati persistenti** su Turso (SQLite distribuito, piano gratuito)

## Struttura del progetto
```
finanze-streamlit/
├── app.py                          # Home / dashboard
├── db.py                           # Livello dati (Turso / SQLite locale)
├── pages/
│   ├── 1_💰_Conti.py
│   ├── 2_💸_Transazioni.py
│   ├── 3_📊_Budget.py
│   ├── 4_🔄_Ricorrenti.py
│   └── 5_🐷_Obiettivi.py
├── data/                           # DB SQLite locale (solo se non usi Turso)
├── .streamlit/secrets.toml.example # Template per le credenziali Turso
├── requirements.txt
└── .gitignore
```

## 1. Crea un database Turso gratuito

Il piano gratuito di Turso include 5 GB di storage e 500 database — abbondante per un uso personale.

1. Crea un account su [turso.tech](https://turso.tech) (puoi accedere con GitHub).
2. Installa la CLI (oppure usa la dashboard web, che non richiede installazione):
   ```bash
   curl -sSfL https://get.tur.so/install.sh | bash
   turso auth login
   ```
3. Crea il database:
   ```bash
   turso db create finanze-massimo
   ```
4. Recupera l'URL di connessione:
   ```bash
   turso db show finanze-massimo --url
   ```
   Otterrai qualcosa come `libsql://finanze-massimo-tuonome.turso.io`.
5. Crea un token di autenticazione:
   ```bash
   turso db tokens create finanze-massimo
   ```
   Copia il token generato (è una stringa lunga tipo JWT).

Se preferisci non usare la CLI, puoi fare gli stessi passaggi dalla dashboard web di Turso (New Database → poi nella pagina del DB trovi sia l'URL che la sezione per generare un token).

## 2. Configura le credenziali

**In locale**, copia il file di esempio e compilalo:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
poi apri `.streamlit/secrets.toml` e incolla URL e token. Questo file è già escluso da `.gitignore`: non verrà mai caricato su GitHub.

**Su Streamlit Community Cloud**, dopo aver fatto il deploy dell'app:
1. Vai su **Manage app** (in basso a destra) → **Settings** → **Secrets**.
2. Incolla:
   ```toml
   TURSO_DATABASE_URL = "libsql://finanze-massimo-tuonome.turso.io"
   TURSO_AUTH_TOKEN = "il-tuo-token"
   ```
3. Salva: l'app si riavvia automaticamente con il database collegato.

Se non configuri questi secrets, l'app funziona comunque usando un file SQLite locale (utile per provarla), ma su Streamlit Cloud quel file **non è persistente** tra i riavvii — è il comportamento della versione precedente.

## 3. Deploy su Streamlit Community Cloud

1. Carica tutti i file di questa cartella su un nuovo repository GitHub (struttura inclusa, cartella `pages/` compresa; **non** caricare `.streamlit/secrets.toml` se lo hai creato in locale — è comunque escluso automaticamente).
2. Vai su [share.streamlit.io](https://share.streamlit.io), accedi con GitHub.
3. **New app** → seleziona il repository e il branch → file principale `app.py` → **Deploy**.
4. Configura i secrets come al punto 2.

Nella dashboard dell'app, sotto il titolo, trovi un'etichetta che conferma se stai usando Turso (🟢) o il DB locale (🟡).

## Esecuzione locale
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Note
- La libreria usata è `libsql-client`, il client Python ufficiale del progetto libSQL/Turso, compatibile con la sintassi SQLite che già usi negli altri progetti (SuperEnalotto, Sereno, ecc.).
- Il cambio di database non richiede modifiche alle pagine (`pages/*.py`): l'interfaccia delle funzioni in `db.py` è rimasta identica.
- Se in futuro vuoi tornare a SQLite puramente locale, basta non impostare i secrets Turso: l'app userà automaticamente `data/finance.db`.

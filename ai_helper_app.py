
import streamlit as st
import openai
import pdfplumber
import docx
import openpyxl
import email
from email import policy
from email.parser import BytesParser
import base64
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# --- Configurazione OpenAI ---
openai.api_key = st.secrets["OPENAI_API_KEY"]
MODEL_NAME = "gpt-4o"
TEMPERATURE = 0.5
MAX_TOKENS = 4500

# --- Configurazione Google Sheets ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    json.loads(st.secrets["GOOGLE_CREDENTIALS"]),
    scopes=scope
)
client = gspread.authorize(credentials)
sheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1

# --- Funzioni per lettura file ---
def read_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def read_excel(file):
    wb = openpyxl.load_workbook(file, data_only=True)
    sheet_data = wb.active
    return "\n".join([
        " | ".join([str(cell) if cell else "" for cell in row])
        for row in sheet_data.iter_rows(values_only=True)
    ])

def read_eml(file):
    msg = BytesParser(policy=policy.default).parse(file)
    return msg.get_body(preferencelist=('plain')).get_content()

def get_file_text(files):
    combined = ""
    for file in files:
        if file.type == "application/pdf":
            combined += read_pdf(file)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            combined += read_docx(file)
        elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            combined += read_excel(file)
        elif file.type == "message/rfc822":
            combined += read_eml(file)
        elif file.type.startswith("text/"):
            combined += file.read().decode("utf-8")
        else:
            combined += f"\n[File non supportato: {file.name}]"
    return combined

# --- Callback per reset ---
def reset_fields():
    st.session_state["input_text"] = ""
    st.session_state["result"] = ""
    st.session_state["rating"] = 3
    st.session_state["comment"] = ""

# --- Layout ---
st.set_page_config(layout="wide", page_title="AI Mail Assistant", page_icon="📩")
st.image("logo.png", width=180)

# Inizializza session state
if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""
if "result" not in st.session_state:
    st.session_state["result"] = ""
if "rating" not in st.session_state:
    st.session_state["rating"] = 3
if "comment" not in st.session_state:
    st.session_state["comment"] = ""

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("## 📨 Nuova Analisi")
    email_text = st.text_area(
        "✍️ Inserisci l'email o testo da analizzare",
        value=st.session_state["input_text"],
        height=180,
        key="input_text"
    )
    uploaded_files = st.file_uploader(
        "📎 Allega file (PDF, DOCX, XLSX, EML, TXT)",
        accept_multiple_files=True,
        type=["pdf", "docx", "xlsx", "eml", "txt"]
    )

    if st.button("🔍 Avvia Analisi"):
        full_input = st.session_state["input_text"].strip()
        if uploaded_files:
            full_input += "\n\n" + get_file_text(uploaded_files)

        if full_input:
            with st.spinner("🧠 Analisi in corso..."):
                try:
                    with open("prompt_template.txt", "r") as f:
                        prompt_template = f.read()
                    prompt = f"{prompt_template}\n\nEmail da analizzare:\n{full_input}"
                    response = openai.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "Sei un assistente utile e professionale."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS
                    )
                    result = response.choices[0].message.content
                    st.session_state["result"] = result

                    # Scrive subito sullo sheet
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([now, st.session_state["input_text"], result, "", ""])

                except Exception as e:
                    st.error(f"Errore durante l'elaborazione o il salvataggio: {e}")
        else:
            st.warning("⚠️ Inserisci testo o carica un file.")

    # Bottone Nuova Analisi con callback
    st.button("🔄 Nuova Analisi", on_click=reset_fields)

with col2:
    st.markdown("## 💡 Risultato")
    if st.session_state["result"]:
        st.text_area("Risposta AI", st.session_state["result"], height=400)

# --- Feedback ---
if st.session_state["result"]:
    st.markdown("---")
    st.markdown("### 💬 Lascia un feedback sul risultato")
    rating = st.slider("Quanto è utile questa analisi?", 1, 5, value=st.session_state["rating"], key="rating")
    comment = st.text_area("Commenti o suggerimenti", value=st.session_state["comment"], key="comment")

    if st.button("📩 Invia feedback"):
        try:
            all_values = sheet.get_all_values()
            last_row = len(all_values)
            # Aggiorna le colonne Rating (4) e Commento (5) dell’ultima riga
            sheet.update_cell(last_row, 4, rating)
            sheet.update_cell(last_row, 5, comment)
            st.success("✅ Grazie per il tuo feedback!")
        except Exception as e:
            st.error(f"Errore durante il salvataggio del feedback: {e}")

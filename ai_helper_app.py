
import streamlit as st
import openai
import os
import pdfplumber
import docx
import openpyxl
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
import base64
import gspread
import json
from google.oauth2.service_account import Credentials

# --- Configurazione ---
openai.api_key = st.secrets["OPENAI_API_KEY"]
MODEL_NAME = "gpt-4o"
TEMPERATURE = 0.5
MAX_TOKENS = 6000
GOOGLE_CREDENTIALS = st.secrets["GOOGLE_CREDENTIALS"]
GOOGLE_SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]

# Setup Google Sheets (patchata con json.loads)
credentials = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS))
client = gspread.authorize(credentials)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

st.set_page_config(layout="wide", page_title="AI Mail Assistant", page_icon="📩")

def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def read_excel(file):
    wb = openpyxl.load_workbook(file, data_only=True)
    sheet_data = wb.active
    text = ""
    for row in sheet_data.iter_rows(values_only=True):
        text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
    return text

def read_eml(file):
    msg = BytesParser(policy=policy.default).parse(file)
    return msg.get_body(preferencelist=('plain')).get_content()

def get_file_text(uploaded_files):
    combined_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            combined_text += read_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            combined_text += read_docx(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            combined_text += read_excel(uploaded_file)
        elif uploaded_file.type == "message/rfc822":
            combined_text += read_eml(uploaded_file)
        elif uploaded_file.type.startswith("text/"):
            combined_text += uploaded_file.read().decode("utf-8")
        else:
            combined_text += f"\n[Formato file non supportato: {uploaded_file.name}]"
    return combined_text

# --- Layout ---
st.image("logo.png", width=180)

col1, col2 = st.columns([1, 1])

if "result" not in st.session_state:
    st.session_state["result"] = ""

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""

with col1:
    st.markdown("## 📨 Nuova Analisi")
    st.write("Incolla un testo o carica uno o più file. L'assistente AI analizzerà i contenuti per fornire una sintesi tecnica e operativa.")
    email_text = st.text_area("✍️ Inserisci il contenuto dell'email", value=st.session_state["input_text"], height=180)
    uploaded_files = st.file_uploader("📎 Allega file (PDF, DOCX, XLSX, EML, TXT)", accept_multiple_files=True,
                                       type=["pdf", "docx", "xlsx", "eml", "txt"])
    
    if st.button("🔍 Avvia Analisi"):
        full_input = email_text.strip()
        if uploaded_files:
            full_input += "\n" + get_file_text(uploaded_files)

        if full_input.strip():
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
                    st.session_state["result"] = response.choices[0].message.content
                    st.session_state["input_text"] = email_text
                except Exception as e:
                    st.error(f"Errore durante l'elaborazione: {e}")
        else:
            st.warning("⚠️ Inserisci del testo o carica un file.")

    if st.button("🔄 Nuova Analisi"):
        st.session_state["input_text"] = ""
        st.session_state["result"] = ""
        st.experimental_rerun()

with col2:
    st.markdown("## 🧠 Risultato")
    if st.session_state["result"]:
        st.text_area("Risposta AI", st.session_state["result"], height=400)

        b64 = base64.b64encode(st.session_state["result"].encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="analisi_ai.txt">📄 Scarica il risultato come file .txt</a>'
        st.markdown(href, unsafe_allow_html=True)

if st.session_state["result"]:
    st.markdown("---")
    st.markdown("### 💬 Lascia un feedback sul risultato")
    rating = st.slider("Quanto è utile questa analisi?", 1, 5, value=3)
    comment = st.text_area("Commenti o suggerimenti")

    if st.button("📩 Invia feedback"):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, st.session_state["input_text"], st.session_state["result"], rating, comment])
            st.success("✅ Grazie per il tuo feedback!")
            st.session_state["input_text"] = ""
            st.session_state["result"] = ""
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Errore durante il salvataggio del feedback: {e}")

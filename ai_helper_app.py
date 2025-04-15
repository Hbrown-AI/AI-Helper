
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

# --- Configurazione ---
openai.api_key = st.secrets["OPENAI_API_KEY"]
MODEL_NAME = "gpt-4o"
TEMPERATURE = 0.5
MAX_TOKENS = 6000

st.set_page_config(layout="wide", page_title="AI Mail Assistant", page_icon="📩")

# --- Funzioni per lettura file ---
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
    sheet = wb.active
    text = ""
    for row in sheet.iter_rows(values_only=True):
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

with col1:
    st.markdown("## 📨 Nuova Analisi")
    st.write("Incolla un testo o carica uno o più file. L'assistente AI analizzerà i contenuti per fornire una sintesi tecnica e operativa.")
    email_text = st.text_area("✍️ Inserisci il contenuto dell'email", height=180)
    uploaded_files = st.file_uploader("📎 Allega file (PDF, DOCX, XLSX, EML, TXT)", accept_multiple_files=True,
                                       type=["pdf", "docx", "xlsx", "eml", "txt"])
    analyze = st.button("🔍 Avvia Analisi")

with col2:
    st.markdown("## 🧠 Risultato")
    output_area = st.empty()

# --- Logica Analisi ---
if analyze:
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
                result = response.choices[0].message.content
                output_area.text_area("Risposta AI", result, height=250)
            except Exception as e:
                st.error(f"Errore durante l'elaborazione: {e}")
    else:
        st.warning("⚠️ Inserisci del testo o carica un file.")

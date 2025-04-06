
import streamlit as st
from openai import OpenAI
import os
import pdfplumber
import docx
import openpyxl
from PIL import Image
import email
from io import BytesIO
from datetime import datetime
import csv

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 2000

def extract_content_from_file(file):
    file_type = file.type
    if file_type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        return text
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(file)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return text
    elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        wb = openpyxl.load_workbook(file)
        sheet = wb.active
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(' '.join([str(cell) for cell in row if cell is not None]))
        return '\n'.join(data)
    elif file_type in ["image/jpeg", "image/png"]:
        image = Image.open(file)
        return f"Immagine caricata: {file.name} - Dimensioni: {image.size}"
    elif file_type == "message/rfc822":
        msg = email.message_from_bytes(file.read())
        text_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_content += payload.decode("utf-8", errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_content = payload.decode("utf-8", errors="ignore")
        return text_content
    else:
        return "Formato file non supportato."

def generate_prompt(email_content, prompt_template):
    return prompt_template + "\nEmail da analizzare:\n" + email_content + "\n"

def save_to_log(email_content, analysis_type, priority, prompt_used, result, rating):
    log_file = "user_logs.csv"
    file_exists = os.path.isfile(log_file)
    with open(log_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Data e Ora", "Email Analizzata", "Tipo di Analisi", "Priorità", "Prompt Inviato", "Risultato Generato", "Rating Cliente"])
        writer.writerow([datetime.now(), email_content, analysis_type, priority, prompt_used, result, rating])

def load_prompt_template():
    try:
        with open("prompt_template.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Analizza la seguente email e rispondi ai seguenti punti:"

st.set_page_config(page_title="AI Helper - Ilmap", layout="centered")
st.title("🔍 AI Helper - Analisi Automatica delle Email")
email_content = st.text_area("Incolla qui il contenuto dell'email o testo da analizzare", height=200)
uploaded_files = st.file_uploader("Carica file da analizzare (.eml, .pdf, .docx, .xlsx, .jpg, .png)", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        email_content += "\n\n" + extract_content_from_file(uploaded_file)

prompt_template = load_prompt_template()

if st.button("🚀 AI Magic - Avvia Analisi"):
    if email_content.strip():
        prompt = generate_prompt(email_content, prompt_template)

        st.markdown("### 🔍 Prompt inviato all'AI")
        st.text_area("Prompt usato per la richiesta", prompt, height=300)

        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "Sei un assistente utile e professionale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            result = response.choices[0].message.content
            st.text_area("Risultato Generato dall'AI", result, height=400)
            rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
            if st.button("✅ Salva il Feedback"):
                save_to_log(email_content, "Analisi Completa", "Alta", prompt, result, rating)
                st.success("Feedback salvato con successo!")
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")
    else:
        st.warning("⚠️ Inserisci del testo o carica un file prima di procedere.")

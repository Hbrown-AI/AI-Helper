
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

# Configurazione dei parametri API nascosti
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 2000

# Funzione per estrarre contenuto dagli allegati
def extract_content_from_file(file):
    file_type = file.type

    if file_type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() + '\n'
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
                    text_content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            text_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        return text_content

    else:
        return "Formato file non supportato."

# Funzione per generare il prompt
def generate_prompt(email_content, prompt_template):
    if not prompt_template.strip():
        prompt_template = "Analizza la seguente email e rispondi ai seguenti punti:"
    if not email_content.strip():
        raise ValueError("Il contenuto dell'email è vuoto. Fornisci un'email valida per l'analisi.")

    prompt = (
        prompt_template + "\n" +
        "Email da analizzare:\n" + email_content + "\n"
    )
    return prompt

# Configurazione della pagina Streamlit
st.set_page_config(page_title="AI Helper - Ilmap", layout="centered")
st.title("🔍 AI Helper - Analisi Automatica delle Email")

# Inserimento manuale testo
st.markdown("### 📥 Incolla qui il testo da analizzare:")
email_content = st.text_area("Incolla qui il contenuto dell'email o testo da analizzare", height=200)

# Upload file multipli
st.markdown("### 📥 Carica file da analizzare (.eml, .pdf, .docx, .xlsx, .jpg, .png):")
uploaded_files = st.file_uploader("Scegli uno o più file", accept_multiple_files=True)

# Estrai contenuti dai file caricati
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_content = extract_content_from_file(uploaded_file)
        email_content += "\n\n" + file_content

# Prompt template
prompt_template = "Analizza la seguente email e rispondi ai seguenti punti:"

# Avvio dell'analisi
if st.button("🚀 AI Magic - Avvia Analisi"):
    if not email_content.strip():
        st.warning("⚠️ Inserisci del testo o carica un file prima di procedere.")
    else:
        prompt = generate_prompt(email_content, prompt_template)

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
            
            st.markdown("### 📋 Risultato dell'Analisi:")
            st.text_area("Risultato Generato dall'AI", result, height=400)
            st.download_button(label="💾 Scarica Report", data=result, file_name="Report_AI_Helper.txt")

            rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
            if st.button("✅ Salva il Feedback"):
                save_to_log(email_content, "Analisi Completa", "Alta", result, rating)
                st.success("Feedback salvato con successo!")

        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")

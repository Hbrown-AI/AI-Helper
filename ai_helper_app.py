import streamlit as st
import openai
import csv
import os
import pdfplumber
import docx
import openpyxl
from PIL import Image
from datetime import datetime
import email
from io import BytesIO

# Configurazione dei parametri API nascosti
openai.api_key = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 2000

# Funzione per estrarre contenuto dagli allegati
def extract_from_eml(file):
    msg = email.message_from_bytes(file.read())
    text_content = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                text_content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            elif part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition"):
                file_name = part.get_filename()
                payload = part.get_payload(decode=True)
                attachments.append((file_name, payload, content_type))
    else:
        text_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

    attachment_texts = []
    for file_name, payload, content_type in attachments:
        attachment_text = f"Allegato: {file_name} ({content_type})\n"
        
        if content_type == "application/pdf":
            with pdfplumber.open(BytesIO(payload)) as pdf:
                text = ''
                for page in pdf.pages:
                    text += page.extract_text() + '\n'
                attachment_text += text

        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(BytesIO(payload))
            text = [paragraph.text for paragraph in doc.paragraphs]
            attachment_text += '\n'.join(text)

        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            wb = openpyxl.load_workbook(BytesIO(payload))
            sheet = wb.active
            data = []
            for row in sheet.iter_rows(values_only=True):
                data.append([str(cell) for cell in row if cell is not None])
            attachment_text += '\n'.join(['\t'.join(row) for row in data])

        elif content_type in ["image/jpeg", "image/png"]:
            image = Image.open(BytesIO(payload))
            attachment_text += f"Immagine caricata: {file_name} - Dimensioni: {image.size}"

        attachment_texts.append(attachment_text)
    
    return text_content, attachment_texts

# Funzione per generare il prompt dinamico
def generate_prompt(email_content, prompt_template):
    # Verifica se il prompt_template è stato fornito
    if not prompt_template.strip():
        prompt_template = "Analizza la seguente email e rispondi ai seguenti punti:"

    # Verifica se il contenuto dell'email è presente
    if not email_content.strip():
        raise ValueError("Il contenuto dell'email è vuoto. Fornisci un'email valida per l'analisi.")
    
    # Combina il prompt_template e l'email_content
    prompt = (
        prompt_template + "\n" +  
        "Email da analizzare:\n" + email_content + "\n"
    )
    return prompt

# Funzione per salvare i dati nel file CSV
def save_to_log(email_content, analysis_type, priority, result, rating):
    log_file = "user_logs.csv"
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        if not file_exists:
            writer.writerow(["Data e Ora", "Email Analizzata", "Tipo di Analisi", "Priorità", "Risultato Generato", "Rating Cliente"])
        
        writer.writerow([datetime.now(), email_content, analysis_type, priority, result, rating])

# Configurazione della pagina
st.set_page_config(page_title="AI Helper - Ilmap", layout="centered")
st.title("🔍 AI Helper - Analisi Automatica delle Email")

# Upload del file .eml
st.markdown("### 📥 Carica un'email (.eml) con allegati:")
uploaded_file = st.file_uploader("Scegli un file .eml", type=["eml"])

email_content = ""
attachment_texts = []

if uploaded_file:
    email_content, attachment_texts = extract_from_eml(uploaded_file)
    st.markdown("### 📧 Contenuto della Email:")
    st.text_area("Testo dell'Email", email_content, height=300)

    if attachment_texts:
        st.markdown("### 📎 Allegati Estratti:")
        for attachment_text in attachment_texts:
            st.text_area("Contenuto Allegato", attachment_text, height=200)

# Parametri di configurazione
analysis_type = "Completa (dettagliata)"
priority = st.selectbox("Priorità", ["Alta", "Media", "Bassa"])

if st.button("🚀 AI Magic - Avvia Analisi"):
    if not email_content.strip():
        st.warning("⚠️ Per favore, carica un'email prima di procedere.")
    else:
        prompt = generate_prompt(email_content, "Analisi della Email")
        
        try:
            response = openai.ChatCompletion.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "Sei un assistente utile e professionale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            result = response['choices'][0]['message']['content']
            
            st.markdown("### 📋 Risultato dell'Analisi:")
            st.text_area("Risultato Generato dall'AI", result, height=400)
            st.download_button(label="💾 Scarica Report", data=result, file_name="Report_AI_Helper.txt")
            
            st.markdown("### 📊 Valuta la tua esperienza:")
            rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
            
            if st.button("✅ Salva il Feedback"):
                save_to_log(email_content, analysis_type, priority, result, rating)
                st.success("Il tuo feedback è stato salvato con successo!")
        
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")


import streamlit as st
import openai
import csv
import os
import mailparser
import pdfplumber
import docx
import openpyxl
from PIL import Image
from datetime import datetime

# Configurazione dei parametri API nascosti
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 2000

# Imposta la tua API Key di OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Funzione per caricare il prompt
def load_prompt():
    try:
        with open("prompt_template.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "Inserisci qui il prompt di default se il file non viene trovato."

# Funzione per generare il prompt dinamico
def generate_prompt(email_content, prompt_template):
    return prompt_template
Email da analizzare:
{email_content}"

# Funzione per salvare i dati nel file CSV
def save_to_log(email_content, result, rating):
    log_file = "user_logs.csv"
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Data e Ora", "Email Analizzata", "Risultato Generato", "Rating Cliente"])
        
        writer.writerow([datetime.now(), email_content, result, rating])

# Funzione per elaborare file caricati
def read_file(file):
    file_type = file.type
    
    if file_type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            text = ''.join([page.extract_text() for page in pdf.pages])
        return text

    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(file)
        return '
'.join([paragraph.text for paragraph in doc.paragraphs])

    elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        wb = openpyxl.load_workbook(file)
        sheet = wb.active
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(' '.join([str(cell) for cell in row if cell]))
        return '
'.join(data)

    elif file_type in ["image/jpeg", "image/png"]:
        image = Image.open(file)
        return f"Immagine caricata: {file.name}, Dimensioni: {image.size}"

    elif file_type == "message/rfc822":
        email = mailparser.parse_from_bytes(file.read())
        text = email.body
        attachments_text = []
        
        for att in email.attachments:
            if att["content_type"] in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "image/jpeg", "image/png"]:
                attachments_text.append(f"Allegato: {att['filename']} (Tipo: {att['content_type']})")

        return text + "

" + "
".join(attachments_text)

    else:
        return "Formato file non supportato."

# Inizializzazione dell'interfaccia Streamlit
st.set_page_config(page_title="AI Helper - Ilmap", layout="centered")
st.title("🔍 AI Helper - Analisi Automatica delle Email")

# Caricamento del prompt e visualizzazione
prompt_template = load_prompt()
st.markdown("### 🔍 Prompt Personalizzato")
prompt_template = st.text_area("Modifica il prompt qui:", prompt_template, height=300)

# Caricamento del file
uploaded_file = st.file_uploader("Carica un file (PDF, Word, Excel, JPG, .eml)", type=["pdf", "docx", "xlsx", "jpg", "png", "eml"])

result = None

if uploaded_file:
    email_content = read_file(uploaded_file)
    
    if not email_content:
        st.warning("⚠️ Il file caricato non contiene testo valido.")
    else:
        prompt = generate_prompt(email_content, prompt_template)
        
        if st.button("🚀 AI Magic - Avvia Analisi"):
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
                st.text_area("📋 Risultato dell'Analisi:", result, height=400)
                st.download_button(label="💾 Scarica Report", data=result, file_name="Report_AI_Helper.txt")
            except Exception as e:
                st.error(f"Errore durante l'elaborazione: {e}")

if result:
    rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
    if st.button("✅ Salva il Feedback"):
        save_to_log(email_content, result, rating)
        st.success("Feedback salvato con successo! Grazie per il tuo contributo.")

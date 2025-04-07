
import streamlit as st
from openai import OpenAI
import os
import pdfplumber
import docx
import openpyxl
from PIL import Image
import email
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configura OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 2000

# Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(eval(os.getenv("GOOGLE_CREDENTIALS")), scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1N4XRmuACsYxof40ZnG_RGKDjdv8SYY3HAXLO0xk3BhE").sheet1

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
        return '\n'.join([p.text for p in doc.paragraphs])
    elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        wb = openpyxl.load_workbook(file)
        sheet_data = wb.active
        return '\n'.join([' '.join([str(cell) for cell in row if cell]) for row in sheet_data.iter_rows()])
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

def load_prompt_template():
    try:
        with open("prompt_template.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Analizza la seguente email e rispondi ai seguenti punti:"

def generate_prompt(email_content, prompt_template):
    return prompt_template + "\nEmail da analizzare:\n" + email_content + "\n"

def save_to_google_sheet(email_content, analysis_type, priority, prompt_used, result, rating='', comment=''):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        email_content,
        analysis_type,
        priority,
        prompt_used,
        result,
        rating,
        comment
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")

if "email_content" not in st.session_state:
    st.session_state["email_content"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = ""
if "last_prompt" not in st.session_state:
    st.session_state["last_prompt"] = ""

st.set_page_config(page_title="AI Mail Summarizer", layout="centered")

# ✅ Mostra il logo all'inizio della pagina
st.image("logo.png", width=150)

st.markdown("""
<h1 style='text-align: center; font-size: 3em;'>📩 AI Mail Summarizer</h1>
<p style='text-align: center; font-size: 1.2em; color: gray;'>Sintesi automatica e tracciamento delle comunicazioni tecniche</p>
""", unsafe_allow_html=True)

if st.button("🔄 Nuova Analisi"):
    st.session_state["email_content"] = ""
    st.session_state["last_result"] = ""
    st.session_state["last_prompt"] = ""

email_content = st.text_area("Incolla qui il contenuto dell'email o testo da analizzare", 
                             value=st.session_state["email_content"], height=200)
uploaded_files = st.file_uploader("Carica file (.eml, .pdf, .docx, .xlsx, .jpg, .png)", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        email_content += "\n\n" + extract_content_from_file(uploaded_file)

prompt_template = load_prompt_template()
result = None

if st.button("🚀 AI Magic - Avvia Analisi"):
    if email_content.strip():
        st.session_state["email_content"] = email_content
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
            st.session_state["last_result"] = result
            st.session_state["last_prompt"] = prompt

            st.text_area("Risultato Generato dall'AI", result, height=400)

            save_to_google_sheet(email_content, "Analisi Completa", "Alta", prompt, result)

            st.download_button(
                label="📄 Scarica il risultato come file .txt",
                data=result,
                file_name="risultato_ai.txt",
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")
    else:
        st.warning("⚠️ Inserisci del testo o carica un file prima di procedere.")

if st.session_state["last_result"]:
    st.subheader("💬 Lascia un feedback sul risultato")
    with st.form("feedback_form"):
        rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
        comment = st.text_area("Hai suggerimenti o commenti?")
        submitted = st.form_submit_button("✅ Invia feedback")
        if submitted:
            save_to_google_sheet(
                st.session_state["email_content"],
                "Analisi Completa",
                "Alta",
                st.session_state["last_prompt"],
                st.session_state["last_result"],
                rating,
                comment
            )
            st.success("✅ Feedback salvato con successo!")
            st.session_state["email_content"] = ""
            st.session_state["last_result"] = ""
            st.session_state["last_prompt"] = ""

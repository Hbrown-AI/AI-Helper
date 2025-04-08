
import streamlit as st
import openai
import base64
import os
from datetime import datetime
from dotenv import load_dotenv

# Carica le variabili d'ambiente da secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
GOOGLE_SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS = st.secrets["GOOGLE_CREDENTIALS"]

# Configura la pagina
st.set_page_config(page_title="AI Mail Assistant", layout="wide")

# Logo in alto
st.image("logo.png", width=150)

# Titolo centrale
st.markdown("<h1 style='text-align: center;'>📩 AI Mail Assistant</h1>", unsafe_allow_html=True)

# Colonne per layout side-by-side
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📨 Nuova Analisi")
    st.write("Incolla il contenuto dell'email o carica un file per iniziare l'analisi.")
    
    input_text = st.text_area("✍️ Inserisci qui il contenuto dell'email", height=250, label_visibility="collapsed")
    uploaded_files = st.file_uploader("📎 Oppure carica uno o più file", type=["pdf", "docx", "xlsx", "eml", "txt"], accept_multiple_files=True)

    analyze_button = st.button("🔍 Nuova Analisi")

with col2:
    st.markdown("### 🧠 Risultato")
    output_placeholder = st.empty()

# Analisi
if analyze_button:
    full_input = input_text.strip()
    if not full_input and not uploaded_files:
        st.warning("⚠️ Inserisci del testo o carica almeno un file.")
    else:
        if uploaded_files:
            for file in uploaded_files:
                file_text = file.read().decode("utf-8", errors="ignore")
                full_input += "\n" + file_text

        with st.spinner("Analisi in corso..."):
            with open("prompt_template.txt", "r") as file:
                prompt_template = file.read()
            prompt = f"{prompt_template}\n\nEmail da analizzare:\n{full_input}"
            response = openai.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "Sei un assistente utile e professionale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2048
            )
            result = response.choices[0].message.content
            output_placeholder.text_area("🧠 Risultato", result, height=250)

            # Download
            b64 = base64.b64encode(result.encode()).decode()
            href = f'<a href="data:file/txt;base64,{b64}" download="risultato_ai.txt">📄 Scarica il risultato</a>'
            st.markdown(href, unsafe_allow_html=True)

            # Feedback
            st.markdown("### ⭐ Lascia un feedback")
            feedback = st.slider("Valuta il risultato da 1 a 5", 1, 5, 3)
            comment = st.text_input("💬 Hai suggerimenti o commenti?")

            if st.button("📤 Invia feedback"):
                from google.oauth2.service_account import Credentials
                import gspread

                credentials = Credentials.from_service_account_info(eval(GOOGLE_CREDENTIALS))
                client = gspread.authorize(credentials)
                sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([now, full_input, result, feedback, comment])
                st.success("✅ Feedback salvato con successo!")

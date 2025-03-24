
import streamlit as st
import openai
import csv
import os
from datetime import datetime

# Imposta la tua API Key di OpenAI
import os
openai.api_key = os.getenv("OPENAI_API_KEY")

# Caricamento del prompt dal file esterno
def load_prompt():
    with open("prompt_template.txt", "r") as file:
        prompt_template = file.read()
    return prompt_template

# Funzione per generare il prompt dinamicamente
def generate_prompt(email_content, analysis_type, priority):
    prompt_template = load_prompt()
    prompt = f"""
    {prompt_template}
    
    Analisi tipo: {analysis_type}
    Priorità dichiarata: {priority}
    
    Email da analizzare:
    {email_content}
    """
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

st.set_page_config(page_title="AI Helper - Ilmap", layout="centered")
st.title("🔍 AI Helper - Analisi Automatica delle Email")

email_content = st.text_area("Incolla qui il contenuto dell'email", height=300)

col1, col2 = st.columns(2)
with col1:
    analysis_type = st.selectbox("Tipo di Analisi", ["Standard (veloce)", "Completa (dettagliata)"])
    temperature = st.slider("Temperatura (Creatività)", 0.0, 1.0, 0.5)
    max_tokens = st.slider("Numero massimo di token", 500, 3000, 2000)
    
with col2:
    priority = st.selectbox("Priorità", ["Alta", "Media", "Bassa"])
    model_name = st.selectbox("Modello OpenAI", ["gpt-4", "gpt-3.5-turbo"])

result = None

if st.button("🚀 AI Magic - Avvia Analisi"):
    if not email_content.strip():
        st.warning("⚠️ Per favore, incolla l'email da analizzare prima di procedere.")
    else:
        prompt = generate_prompt(email_content, analysis_type, priority)
        
        try:
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Sei un assistente utile e professionale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            result = response['choices'][0]['message']['content']
            
            st.markdown("### 📋 Risultato dell'Analisi:")
            st.text_area("Risultato Generato dall'AI", result, height=400)
            st.download_button(label="💾 Scarica Report", data=result, file_name="Report_AI_Helper.txt")
        
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")

if result:
    st.markdown("### 📊 Valuta la tua esperienza:")
    rating = st.slider("Quanto sei soddisfatto del risultato?", 1, 5)
    
    if st.button("✅ Salva il Feedback"):
        save_to_log(email_content, analysis_type, priority, result, rating)
        st.success("Il tuo feedback è stato salvato con successo! Grazie per aver contribuito a migliorare l'applicazione.")

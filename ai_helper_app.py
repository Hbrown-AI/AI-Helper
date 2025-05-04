import streamlit as st
import openai
import base64

# Configurazione base per testare il rendering dell'output con markdown
st.set_page_config(layout="wide", page_title="AI Mail Assistant", page_icon="📩")

if "result" not in st.session_state:
    st.session_state["result"] = ""

# Input di esempio
st.text_area("✍️ Inserisci l'email o testo da analizzare", key="input_text")

# Simula un output AI
if st.button("🔍 Avvia Analisi"):
    st.session_state["result"] = """
## 🔍 Analisi completata
- 📝 **Sintesi:** Questo è un esempio di output con emoji e **Markdown**.
- 📅 Data: 2024-04-25
"""

# Output con Markdown e emoji
if st.session_state["result"]:
    st.markdown(st.session_state["result"], unsafe_allow_html=True)
    b64 = base64.b64encode(st.session_state["result"].encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="analisi_ai.txt">📄 Scarica il risultato come file .txt</a>'
    st.markdown(href, unsafe_allow_html=True)
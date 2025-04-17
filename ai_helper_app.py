import gspread
from google.oauth2.service_account import Credentials

# Configura OpenAI
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 4500

# Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(eval(os.getenv("GOOGLE_CREDENTIALS")), scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1N4XRmuACsYxof40ZnG_RGKDjdv8SYY3HAXLO0xk3BhE").sheet1


import streamlit as st
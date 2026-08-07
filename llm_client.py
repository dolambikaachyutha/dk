from google import genai
import streamlit as st

client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)

MODEL = "gemini-3.6-flash"

def ask_ai(prompt):

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text
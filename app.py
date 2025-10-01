import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("Error: DATABASE_URL is not available in the .env file")
    st.stop()

engine = create_engine(DATABASE_URL)
st.title("Violation Tracking Table")

with st.sidebar:
    st.header("Chat History")
    if st.button("New Chat"):
        print("HIIII")

st.write("Current Violations in the System")
st.dataframe()
st.subheader("Ask questions about violations")

user_question = st.chat_input("Ask database (Ex: How many violations are recorded in the system?)")
if user_question:
    pass
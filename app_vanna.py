import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote

# Import Vanna classes
from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore

# Load environment variables from .env file
load_dotenv()

# --- Vanna Setup ---
# This setup is copied from your vanna_train.py file to ensure consistency.
# In a real project, you might move this class to a separate shared file.
class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

# Initialize Vanna with your specific model
# The vn object holds the connection and the trained knowledge.
@st.cache_resource
def setup_vanna():
    """Initializes and connects the Vanna instance."""
    vn = MyVanna(config={'model': 'hf.co/mradermacher/natural-sql-7b-i1-GGUF:Q4_K_M'})

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not found in .env file. Please provide it.")
        st.stop()

    p = urlparse(db_url)
    vn.connect_to_postgres(
        host=p.hostname,
        dbname=p.path.lstrip('/'),
        user=p.username,
        password=unquote(p.password) if p.password else None,
        port=p.port or 5432
    )
    return vn

vn = setup_vanna()

# --- Streamlit UI ---
st.title("Bảng theo dõi vi phạm")
st.write("Sử dụng Vanna để truy vấn database bằng ngôn ngữ tự nhiên.")

# Display the full table as in the original app
@st.cache_data
def fetch_all_violations():
    """Fetches all data from the violations table."""
    return vn.run_sql("SELECT * FROM violations")

violations_df = fetch_all_violations()
st.dataframe(violations_df, use_container_width=True)

st.subheader("Ask questions about violations")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "df" in message and message["df"] is not None:
            st.dataframe(message["df"])
        if "sql" in message and message["sql"] is not None:
            st.code(message["sql"], language="sql")
        if "fig" in message and message["fig"] is not None:
            st.plotly_chart(message["fig"])

# Accept user input
if user_question := st.chat_input("Hôm nay có mấy người vi phạm?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_question})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_question)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý câu hỏi..."):
            try:
                # This is the core Vanna function that replaces the entire Haystack pipeline
                sql, df, fig = vn.ask(question=user_question, print_results=False)

                assistant_response = {"role": "assistant", "content": "Here are the results:", "sql": sql, "df": df, "fig": fig}

                if fig is not None:
                    st.plotly_chart(fig)
                    assistant_response["content"] = "I've generated a chart for you:"
                elif df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    # If no data or chart, Vanna might still provide a text answer
                    # For this demo, we'll use a standard message.
                    assistant_response["content"] = "I couldn't find any data for your question."
                    st.write(assistant_response["content"])


                # Display the generated SQL in an expander
                if sql:
                    with st.expander("Generated SQL Query"):
                        st.code(sql, language="sql")

                # Display follow-up questions if available
                #if followup_questions:
                #    st.write("**Suggested follow-up questions:**")
                #    for q in followup_questions:
                #        st.markdown(f"- {q}")

                st.session_state.messages.append(assistant_response)

            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
import pandas as pd
import streamlit as st
import re
import os
from dotenv import load_dotenv
from haystack import component
from haystack import Pipeline
from haystack.utils import Secret
from haystack.components.routers import ConditionalRouter
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.generators.ollama import OllamaGenerator
from sqlalchemy import create_engine, text, inspect
import json
import time 
import uuid 

# RAG imports
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersTextEmbedder
from template.prompt import SQL_PROMPT_TEMPLATE, EXPLAIN_PROMPT_TEMPLATE
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.dataclasses import Document
from haystack.components.joiners import DocumentJoiner
from haystack.document_stores.in_memory import InMemoryDocumentStore

load_dotenv()
MODEL_NAME = "hf.co/mradermacher/natural-sql-7b-i1-GGUF:Q4_K_M"
# Create database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("Error: DATABASE_URL is not available in the .env file")
    st.stop()
engine = create_engine(DATABASE_URL)

# log file for analytics
log_path = "output/logs/results.jsonl"
os.makedirs(os.path.dirname(log_path), exist_ok= True)

def _json_serializer(obj):
    if isinstance(obj, ChatMessage):
        return {
            "content": obj.text,
            "role": obj.role.name,
            "meta": obj.meta
        }
    if isinstance(obj, Document):
        return {
            "id": obj.id,
            "content": obj.content[:200] if obj.content else "",
            "score": obj.score,
            "meta": obj.meta
        }
    raise TypeError(f"Object of type '{type(obj).__name__}' is not JSON serializable")

def save_result(data: dict, path: str):
    """
    Saves the dictionary to a JSONL file, correctly handling ChatMessage objects.
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=_json_serializer, ensure_ascii=False) + "\n")

def save_chat_history_to_db(engine, session_id, chat_history):
    with engine.connect() as connection:
        with connection.begin() as transaction:
            try:
                messsages_to_save = [
                    {"role": msg.role.name.lower(), "content": msg.text}
                    for msg in chat_history
                ]

                connection.execute(text("DELETE FROM chat_messages WHERE session_id = :session_id"), {"session_id": session_id})
                for message in messsages_to_save:
                    stmt = text(
                        """
                        INSERT INTO chat_messages(session_id, role, content)
                        VALUES (:session_id, :role, :content)
                        """
                    )
                    connection.execute(stmt, {
                        "session_id": session_id,
                        "role": message["role"],
                        "content": message["content"]
                    })

            except Exception as e:
                st.error(f"Error saving chat history: {e}")
                raise

def get_chat_sessions(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT id, start_time FROM chat_sessions ORDER BY start_time DESC"))
        return result.fetchall()    

def load_chat_history(engine, session_id):
    """Load chat message history for a specific chat session."""
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT role, content FROM chat_messages WHERE session_id = :session_id ORDER BY timestamp ASC"),
            {"session_id": session_id}
        )
        # Convert database results into a list of ChatMessage objects
        history = []
        for row in result.fetchall():
            role, content = row
            if role == 'user':
                history.append(ChatMessage.from_user(content))
            else:
                history.append(ChatMessage.from_assistant(content))
        return history

@st.cache_data
def get_table_schema(table_name):
    """
    Fetches the schema of a given table and formats it as a string.
    Uses the global 'engine' object.
    """
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        
        schema_str = f'Table "{table_name}" has the following columns:\n'
        for column in columns:
            col_name = column['name']
            col_type = str(column['type'])
            schema_str += f'- {col_name} ({col_type})\n'
            
        return schema_str
    except Exception as e:
        return f"Could not inspect table '{table_name}'. Error: {e}"

def fetch_all_violations():
    with engine.connect() as connection:
        df = pd.read_sql("SELECT * FROM violations", connection)
        return df


# Custom components 
@component
class MDconverter:
    def __init__(self):
        pass
    @component.output_types(str_queries = list[str])
    def run(self, replies: list[str]):
        def extract_sql(text: str) -> str:
            m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S)
            return m.group(1).strip() if m else text.strip()
        str_queries = []
        for text_reply in replies:
            extracted = extract_sql(text_reply)
            str_queries.append(extracted)
        return {'str_queries': str_queries}
    
@component
class SQLQuery:
    def __init__(self, engine):
        self._engine = engine
        # No need to keep connection here, will manage in run function
        # self.connection = self._engine.connect()

    @component.output_types(results=list[str], queries = list[str])
    def run(self, sql_queries: list[str]):
        results = []
        
        for query in sql_queries:
            try:
                # Use 'with' to ensure connection is properly closed
                with self._engine.connect() as connection:
                    # Execute query and get results
                    cursor_result = connection.execute(text(query))
                    
                    # Check if query returns rows (e.g., SELECT)
                    if cursor_result.returns_rows:
                        # Get all rows and column names
                        rows = cursor_result.fetchall()
                        columns = cursor_result.keys()
                        # Create DataFrame from results
                        result_df = pd.DataFrame(rows, columns=columns)
                        results.append(result_df.to_string())
                    else:
                        # For queries that don't return rows (e.g., UPDATE, INSERT)
                        results.append(f"Query executed successfully, {cursor_result.rowcount} rows affected.")

            except Exception as e:
                results.append(f"SQL Error: {str(e)}")
        return {'results': results, 'queries': sql_queries}

@st.cache_resource
def setup_pipeline():
    # RAG components - Pgvector for semantic search
    document_store = PgvectorDocumentStore(
        connection_string= Secret.from_env_var("DATABASE_URL"),
        table_name="haystack_documents_v2",
        embedding_dimension = 384 
    )
    text_embedder = SentenceTransformersTextEmbedder(model="all-MiniLM-L6-v2")
    
    # Semantic retriever (reduced from 3 to 2 since we'll add BM25)
    semantic_retriever = PgvectorEmbeddingRetriever(
        document_store=document_store, 
        top_k=2
    )

    # NEW: BM25 setup
    # Load documents from pgvector into memory for BM25
    all_docs = document_store.filter_documents()
    bm25_store = InMemoryDocumentStore()
    bm25_store.write_documents(all_docs)
    
    bm25_retriever = InMemoryBM25Retriever(
        document_store=bm25_store,
        top_k=2
    )
    
    # NEW: Joiner with deduplication
    joiner = DocumentJoiner(
        join_mode="reciprocal_rank_fusion",  # This already deduplicates by default
        top_k=3,  # Limit final output to 3 documents
        sort_by_score=True  # Ensure best documents come first
    )

    # Existing components
    sql_query = SQLQuery(engine)
    prompt = PromptBuilder(template=SQL_PROMPT_TEMPLATE)
    llm = OllamaGenerator(model = MODEL_NAME, keep_alive= -1)
    converter = MDconverter()

    explain_prompt = PromptBuilder(template=EXPLAIN_PROMPT_TEMPLATE)
    llm_explainer = OllamaGenerator(model= MODEL_NAME)

    routes = [
        {
            "condition": "{{'no_answer' not in str_queries[0].lower()}}",
            "output": "{{[str_queries[0]]}}",
            "output_name": "sql",
            "output_type": list[str],
        },
        {
            "condition": "{{'no_answer' in str_queries[0].lower()}}",
            "output": "I cannot answer this question based on the available data. The database contains information about violations with columns for id, employee_name, department, violation_type, area, violation_time, and status. Please try asking a question related to these fields.",
            "output_name": "no_answer",
            "output_type": str,
        },
    ]
    router = ConditionalRouter(routes)

    error_routes = [
        {
            "condition": "{{'SQL Error:' in results[0]}}",
            "output": "{{results[0]}}",
            "output_name": "sql_error",
            "output_type": str,
        },
        {
            "condition": "{{'SQL Error:' not in results[0]}}",
            "output": "{{results}}",
            "output_name": "results_ok",
            "output_type": list[str],
        },
    ]
    error_router = ConditionalRouter(error_routes)

    # Build pipeline
    sql_pipeline = Pipeline()
    
    # Add RAG components
    sql_pipeline.add_component('text_embedder', text_embedder)
    sql_pipeline.add_component('semantic_retriever', semantic_retriever)
    sql_pipeline.add_component('bm25_retriever', bm25_retriever)  # NEW
    sql_pipeline.add_component('joiner', joiner)  # NEW
    
    # Add existing components
    sql_pipeline.add_component('prompt', prompt)
    sql_pipeline.add_component('llm', llm)
    sql_pipeline.add_component('converter', converter)
    sql_pipeline.add_component('router', router)
    sql_pipeline.add_component('sql_querier', sql_query)
    sql_pipeline.add_component('error_router', error_router)
    sql_pipeline.add_component('explain_prompt', explain_prompt)
    sql_pipeline.add_component('llm_explainer', llm_explainer)

    # Connect hybrid retrieval (MODIFIED)
    sql_pipeline.connect("text_embedder.embedding", "semantic_retriever.query_embedding")
    sql_pipeline.connect("semantic_retriever.documents", "joiner.documents")  # NEW
    sql_pipeline.connect("bm25_retriever.documents", "joiner.documents")      # NEW
    sql_pipeline.connect("joiner.documents", "prompt.documents")  # Changed from semantic_retriever

    # Connect existing components
    sql_pipeline.connect("prompt.prompt", "llm.prompt")
    sql_pipeline.connect("llm.replies", "converter.replies")
    sql_pipeline.connect("converter.str_queries", "router.str_queries")
    sql_pipeline.connect("router.sql", "sql_querier.sql_queries")
    sql_pipeline.connect("sql_querier.results", "error_router.results")
    sql_pipeline.connect("error_router.results_ok", "explain_prompt.result")
    sql_pipeline.connect("explain_prompt.prompt", "llm_explainer.prompt")

    return sql_pipeline

# Streamlit UI
st.title("Violation Tracking Table")

with st.sidebar:
    st.header("Chat History")
    if st.button("New Chat"):
        if "session_id" in st.session_state:
            del st.session_state.session_id
        if "chat_history" in st.session_state:
            del st.session_state.chat_history
        st.rerun()

    try:
        past_sessions = get_chat_sessions(engine)
        if not past_sessions:
            st.caption("No past conversations found.")
        else:
            for session in past_sessions:
                session_id, start_time = session
                session_time_str = start_time.strftime("%d %b %Y, %H:%M")
                
                if st.button(f"Chat from {session_time_str}", key=session_id, use_container_width=True):
                    st.session_state.session_id = session_id
                    st.session_state.chat_history = load_chat_history(engine, session_id)
                    st.rerun()
    except Exception as e:
        st.error(f"Error loading chat history: {e}")
        raise

if "session_id" not in st.session_state:
    with engine.connect() as connection:
        with connection.begin() as transaction:
            result = connection.execute(text("INSERT INTO chat_sessions (start_time) VALUES (DEFAULT) RETURNING id"))
            st.session_state.session_id = result.scalar_one()
            st.session_state.chat_history = []
st.write("Current Violations in the System")

violations_df = fetch_all_violations()
st.dataframe(violations_df, use_container_width=True)

st.subheader("Ask questions about violations")

# Display existing chat history
for msg in st.session_state.chat_history:
    role = msg.role.name.lower() if isinstance(msg, ChatMessage) else msg.get("role", "user")
    content = msg.text if isinstance(msg, ChatMessage) else msg.get("content", "")
    with st.chat_message(role):
        st.markdown(content)

user_question = st.chat_input("Ask database (Ex: How many violations are recorded in the system?)")
if user_question:
    st.session_state.chat_history.append(ChatMessage.from_user(user_question))
    with st.chat_message("user"):
        st.markdown(user_question)
    with st.spinner("Processing..."):
        try:
            start_time = time.time()
            sql_pipeline = setup_pipeline()
            history_payload = [
                {"role": m.role.name.lower(), "content": m.text} if isinstance(m, ChatMessage) else m
                for m in st.session_state.chat_history
            ]
            result = sql_pipeline.run({
                "text_embedder": {"text": user_question},
                "bm25_retriever": {"query": user_question},  # NEW: Add BM25 query input
                "prompt": {
                    "question": user_question,
                    "schema": get_table_schema("violations"),
                    "history": history_payload
                },
                "explain_prompt": {"question": user_question},
            }, include_outputs_from=["llm_explainer", "sql_querier", "llm", "prompt", "router", "error_router", "explain_prompt", "joiner"])  # Add "joiner"
            end_time = time.time()
            execution_time = end_time - start_time
            result['execution_time'] = execution_time
            st.session_state.last_result = result
            assistant_text = None
            if "no_answer" in result["router"]:
                assistant_text = result["router"]["no_answer"]
                with st.chat_message("assistant"):
                    st.warning(assistant_text)
            elif "sql_error" in result["error_router"]:
                assistant_text = f"An error occurred while executing SQL:\n{result['error_router']['sql_error']}"
                with st.chat_message("assistant"):
                    st.error(assistant_text)
                    st.code(result['sql_querier']['queries'][0], language='sql')
            elif result["llm_explainer"]["replies"]:
                assistant_text = result['llm_explainer']['replies'][0]
                with st.chat_message("assistant"):
                    st.success(assistant_text)
            if assistant_text:
                st.session_state.chat_history.append(ChatMessage.from_assistant(assistant_text))
            save_chat_history_to_db(engine, st.session_state.session_id, st.session_state.chat_history)
            # Attach chat history snapshot for logging (serializable via custom serializer)
            result['chat_history'] = st.session_state.chat_history
            save_result(result, log_path)
        except Exception as e:
            err_text = f"Error: {str(e)}"
            st.session_state.chat_history.append(ChatMessage.from_assistant(err_text))
            with st.chat_message("assistant"):
                st.error(err_text)
            import traceback
            st.error(traceback.format_exc())

# Add debug expander
with st.expander("Debug Info"):
    if 'last_result' in st.session_state:
        st.write("Information from the last pipeline run:")
        st.json(st.session_state.last_result)
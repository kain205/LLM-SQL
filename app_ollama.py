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
import time # Thêm import time

# RAG imports
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersTextEmbedder

load_dotenv()
# Create database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("Lỗi: Vui lòng cung cấp DATABASE_URL trong file .env")
    st.stop()
engine = create_engine(DATABASE_URL)

# log file for analytics
log_path = "logs/results.jsonl"
os.makedirs(os.path.dirname(log_path), exist_ok= True)
def _json_serializer(obj):
    """
    A simple "translator" that tells json.dumps how to handle a ChatMessage object.
    """
    if isinstance(obj, ChatMessage):
        # Convert the ChatMessage into a simple dictionary
        return {
            "content": obj.text,
            "role": obj.role.name, # .name converts the enum (e.g., ChatRole.USER) to a string ("USER")
            "meta": obj.meta
        }
    # If it's not a ChatMessage, raise an error to let json.dumps handle it.
    raise TypeError(f"Object of type '{type(obj).__name__}' is not JSON serializable")

def save_result(data: dict, path: str):
    """
    Saves the dictionary to a JSONL file, correctly handling ChatMessage objects.
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=_json_serializer, ensure_ascii=False) + "\n")

def get_table_schema(engine, table_name):
    """
    Fetches the schema of a given table and formats it as a string.
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


# Custom components from practice.py
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
        # Không cần giữ connection ở đây, sẽ quản lý trong hàm run
        # self.connection = self._engine.connect()

    @component.output_types(results=list[str], queries = list[str])
    def run(self, sql_queries: list[str]):
        results = []
        
        for query in sql_queries:
            try:
                # Sử dụng 'with' để đảm bảo connection được đóng đúng cách
                with self._engine.connect() as connection:
                    # Thực thi truy vấn và lấy kết quả
                    cursor_result = connection.execute(text(query))
                    
                    # Kiểm tra xem truy vấn có trả về hàng không (ví dụ: SELECT)
                    if cursor_result.returns_rows:
                        # Lấy tất cả các hàng và tên cột
                        rows = cursor_result.fetchall()
                        columns = cursor_result.keys()
                        # Tạo DataFrame từ kết quả
                        result_df = pd.DataFrame(rows, columns=columns)
                        results.append(result_df.to_string())
                    else:
                        # Đối với các truy vấn không trả về hàng (ví dụ: UPDATE, INSERT)
                        results.append(f"Query executed successfully, {cursor_result.rowcount} rows affected.")

            except Exception as e:
                results.append(f"SQL Error: {str(e)}")
        return {'results': results, 'queries': sql_queries}

# Setup Haystack pipeline
def setup_pipeline():
    # RAG components
    document_store = PgvectorDocumentStore(
        connection_string= Secret.from_env_var("DATABASE_URL"),
        table_name="haystack_documents",
        embedding_dimension = 384 
    )
    text_embedder = SentenceTransformersTextEmbedder(model="all-MiniLM-L6-v2")
    retriever = PgvectorEmbeddingRetriever(document_store=document_store, top_k=3)

    # Fetch table schema
    table_schema = get_table_schema(engine, "violations")

    sql_query = SQLQuery(engine)
    template = """Please generate a PostgreSQL query to answer the following question.
                Question: {{question}}

                Here is the database schema for the `violations` table:
                ---
                {{schema}}
                ---

                Here is some additional context from our knowledge base that might be helpful:
                ---
                {% for doc in documents %}
                {{ doc.content }}
                {% endfor %}
                ---
                If the question cannot be answered using this table and these columns, 
                respond exactly with 'no_answer'.
                
                Only return the SQL query without any additional text or explanation.
                Always start your query with SELECT or WITH.
                """
    prompt = PromptBuilder(template=template)
    llm = OllamaGenerator(model="hf.co/second-state/CodeQwen1.5-7B-Chat-GGUF:Q4_K_M", keep_alive= -1)
    converter = MDconverter()

    # New: prompt to explain the result + separate LLM for the explanation
    explain_template = """
    You are an assistant specialized in explaining SQL results in a natural way.
    Task:
    - Read the user's question and the returned SQL result.
    - Provide a concise, easy-to-understand answer, as a human would respond directly.
    - Do not repeat the question, do not restate the raw result, only give the natural answer.

    User question: {{question}}
    SQL Result: {{result[0]}}

    Please answer:
    """
    explain_prompt = PromptBuilder(template=explain_template)
    llm_explainer = OllamaGenerator(model="hf.co/second-state/CodeQwen1.5-7B-Chat-GGUF:Q4_K_M")

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

    sql_pipeline = Pipeline()
    # RAG components
    sql_pipeline.add_component('text_embedder', text_embedder)
    sql_pipeline.add_component('retriever', retriever)
    # Old components
    sql_pipeline.add_component('prompt', prompt)
    sql_pipeline.add_component('llm', llm)
    sql_pipeline.add_component('converter', converter)
    sql_pipeline.add_component('router', router)
    sql_pipeline.add_component('sql_querier', sql_query)

    # New: Router to handle SQL execution errors
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
    sql_pipeline.add_component('error_router', error_router)

    # New components for explain
    sql_pipeline.add_component('explain_prompt', explain_prompt)
    sql_pipeline.add_component('llm_explainer', llm_explainer)

    # Connect RAG components
    sql_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
    sql_pipeline.connect("retriever.documents", "prompt.documents")

    # Connect old components
    sql_pipeline.connect("prompt.prompt", "llm.prompt")
    sql_pipeline.connect("llm.replies", "converter.replies")
    sql_pipeline.connect("converter.str_queries", "router.str_queries")
    sql_pipeline.connect("router.sql", "sql_querier.sql_queries")

    # Route the results from sql_querier to the new error_router
    sql_pipeline.connect("sql_querier.results", "error_router.results")

    # New connections to build explanation (only on success)
    sql_pipeline.connect("error_router.results_ok", "explain_prompt.result")
    sql_pipeline.connect("explain_prompt.prompt", "llm_explainer.prompt")

    return sql_pipeline

# Streamlit UI
st.title("Bảng theo dõi vi phạm")
st.write("Danh sách vi phạm hiện có trong hệ thống")

violations_df = fetch_all_violations()
st.dataframe(violations_df, use_container_width=True)

st.subheader("Ask questions about violations")
user_question = st.text_input("Đặt câu hỏi về database:", placeholder="Ví dụ: Hôm nay có mấy người vi phạm")

if st.button("Send"):
    if user_question:
        with st.spinner("Đang xử lý câu hỏi..."):
            try:
                start_time = time.time() # Bắt đầu tính giờ

                # Initialize pipeline
                sql_pipeline = setup_pipeline()

                # Chạy pipeline với câu hỏi của người dùng và ngữ cảnh mới
                result = sql_pipeline.run({
                    "text_embedder": {"text": user_question},
                    "prompt": {
                        "question": user_question,
                        "schema": get_table_schema(engine, "violations")
                    },
                    "explain_prompt": {"question": user_question},
                }, include_outputs_from= ["llm_explainer", "sql_querier", "llm", "prompt", "router", "error_router", "explain_prompt"])

                end_time = time.time() # Kết thúc tính giờ
                execution_time = end_time - start_time
                result['execution_time'] = execution_time # Thêm thời gian thực thi vào kết quả

                st.session_state.last_result = result

                if "no_answer" in result["router"]:
                    st.warning(result["router"]["no_answer"])
                elif "sql_error" in result["error_router"]:
                    st.error(f"Đã xảy ra lỗi khi thực thi SQL:\n{result['error_router']['sql_error']}")
                    st.code(result['sql_querier']['queries'][0], language='sql')
                elif result["llm_explainer"]["replies"]:
                    explanation = result['llm_explainer']['replies'][0]
                    st.success(explanation)
                save_result(result, log_path)
                # Log for analytics   

            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    else:
        st.warning("Vui lòng nhập câu hỏi")

# Add debug expander
with st.expander("Debug Info"):
    if 'last_result' in st.session_state:
        st.write("Thông tin từ lần chạy pipeline cuối cùng:")
        st.json(st.session_state.last_result)
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
from haystack.dataclasses import ChatMessage, Document
from haystack_integrations.components.generators.ollama import OllamaGenerator
from sqlalchemy import create_engine, inspect, text
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
    # 1. REMOVE the line: data = str(data)

    # 2. Simply pass the dictionary directly to json.dumps,
    #    using our "translator" function for any special objects.
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=_json_serializer, ensure_ascii=False) + "\n")

def fetch_all_violations():
    with engine.connect() as connection:
        df = pd.read_sql("SELECT * FROM violations", connection)
        return df

def get_db_context():
    """
    Lấy schema, dữ liệu mẫu, và các giá trị duy nhất để cung cấp ngữ cảnh cho LLM.
    """
    with engine.connect() as connection:
        # Lấy tên cột
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('violations')]

        # Lấy dữ liệu mẫu
        sample_rows_df = pd.read_sql("SELECT * FROM public.violations LIMIT 3", connection)
        
        # Lấy các giá trị duy nhất cho các cột phân loại
        violation_types = pd.read_sql("SELECT DISTINCT loai_vi_pham FROM public.violations", connection)['loai_vi_pham'].tolist()
        statuses = pd.read_sql("SELECT DISTINCT trang_thai FROM public.violations", connection)['trang_thai'].tolist()
        departments = pd.read_sql("SELECT DISTINCT phong_ban FROM public.violations", connection)['phong_ban'].tolist()
        areas = pd.read_sql("SELECT DISTINCT khu_vuc FROM public.violations", connection)['khu_vuc'].tolist()

        context = {
            "columns": columns,
            "sample_rows": sample_rows_df.to_string(),
            "violation_types": ", ".join(f"'{v}'" for v in violation_types),
            "statuses": ", ".join(f"'{s}'" for s in statuses),
            "departments": ", ".join(f"'{d}'" for d in departments),
            "areas": ", ".join(f"'{a}'" for a in areas)
        }
        return context

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

    sql_query = SQLQuery(engine)
    template = """Please generate a PostgreSQL query to answer the following question.
                Question: {{question}}

                Here is some additional context from our knowledge base that might be helpful:
                ---
                {% for doc in documents %}
                {{ doc.content }}
                {% endfor %}
                ---
                
                Use the table 'public.violations' with these columns: {{columns}}

                Here is some context about the data in the table:
                - The 'loai_vi_pham' column can contain values like: {{violation_types}}.
                - The 'trang_thai' column can contain values like: {{statuses}}.
                - The 'phong_ban' column can contain values like: {{departments}}.
                - The 'khu_vuc' column can contain values like: {{areas}}.
                - The 'thoi_gian_vi_pham' column stores the exact timestamp of the violation.
                - Here are some sample rows from the table:
                {{sample_rows}}
                
                If the question cannot be answered using this table and these columns, 
                respond exactly with 'no_answer'.
                
                Only return the SQL query without any additional text or explanation.
                Always start your query with SELECT or WITH.
                """
    prompt = PromptBuilder(template=template)
    llm = OllamaGenerator(model="hf.co/second-state/CodeQwen1.5-7B-Chat-GGUF:Q4_K_M")
    converter = MDconverter()

    # New: prompt để giải thích kết quả + LLM riêng cho phần giải thích
    explain_template = """
    Bạn là một trợ lý chuyên giải thích kết quả từ SQL theo cách tự nhiên.  
    Nhiệm vụ:  
    - Đọc câu hỏi của người dùng và kết quả SQL trả về.  
    - Trả lời ngắn gọn, dễ hiểu, giống như cách con người trả lời trực tiếp.  
    - Không lặp lại câu hỏi, không nhắc lại kết quả thô, chỉ đưa ra câu trả lời tự nhiên.  

    Câu hỏi của người dùng: {{question}}  
    Kết quả SQL: {{result[0]}}  

    Hãy trả lời:
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
            "output": "I cannot answer this question based on the available data. The database contains information about violations with columns for id, ten_nhan_vien, phong_ban, loai_vi_pham, khu_vuc, thoi_gian_vi_pham, and trang_thai. Please try asking a question related to these fields.",
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
    #sql_pipeline.connect("sql_querier.queries", "explain_prompt.query")
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
                
                # Lấy ngữ cảnh database trước khi chạy pipeline
                db_context = get_db_context()

                # Chạy pipeline với câu hỏi của người dùng và ngữ cảnh mới
                result = sql_pipeline.run({
                    "text_embedder": {"text": user_question},
                    "prompt": {
                        "question": user_question, 
                        **db_context
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
                #log_interaction(user_question, sql_query, query_result_str, explanation, prompt_str)                

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
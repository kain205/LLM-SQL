import pandas as pd
import streamlit as st
import re
import os
from dotenv import load_dotenv
from haystack import component
from haystack import Pipeline
from haystack.components.routers import ConditionalRouter
from haystack.components.builders import ChatPromptBuilder
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.generators.google_genai import GoogleGenAIChatGenerator
from sqlalchemy import create_engine, inspect
import json
from datetime import datetime

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
        violation_types = pd.read_sql("SELECT DISTINCT violation_type FROM public.violations", connection)['violation_type'].tolist()
        statuses = pd.read_sql("SELECT DISTINCT status FROM public.violations", connection)['status'].tolist()

        context = {
            "columns": columns,
            "sample_rows": sample_rows_df.to_string(),
            "violation_types": ", ".join(f"'{v}'" for v in violation_types),
            "statuses": ", ".join(f"'{s}'" for s in statuses)
        }
        return context

# Custom components from practice.py
@component
class MDconverter:
    def __init__(self):
        pass
    @component.output_types(str_queries = list[str])
    def run(self, md_queries: list[ChatMessage]):
        def extract_sql(text: str) -> str:
            m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S)
            return m.group(1).strip() if m else text.strip()      
        str_queries = []
        for md_query in md_queries:
            sql_query = md_query.text
            extracted = extract_sql(sql_query)
            str_queries.append(extracted)
        return {'str_queries': str_queries}
    
@component
class SQLQuery:
    def __init__(self, engine):
        self._engine = engine
        self.connection = self._engine.connect()

    @component.output_types(results=list[str], queries = list[str])
    def run(self, sql_queries: list[str]):
        results = []
        
        for query in sql_queries:
            try:                    
                result = pd.read_sql(query, self.connection)
                results.append(f"{result}")
            except Exception as e:
                results.append(f"SQL Error: {str(e)}")
        return {'results': results, 'queries': sql_queries}

# Setup Haystack pipeline
def setup_pipeline():
    sql_query = SQLQuery(engine)
    template = """Please generate a PostgreSQL query to answer the following question.
                Question: {{question}}
                
                Use the table 'public.violations' with these columns: {{columns}}

                Here is some context about the data in the table:
                - The 'violation_type' column can contain values like: {{violation_types}}.
                - The 'status' column can contain values like: {{statuses}}.
                - Here are some sample rows from the table:
                {{sample_rows}}
                
                If the question cannot be answered using this table and these columns, 
                respond exactly with 'no_answer'.
                
                Only return the SQL query without any additional text or explanation.
                Always start your query with SELECT or WITH.
                """
    prompt = ChatPromptBuilder(template=[ChatMessage.from_user(template)], required_variables=["question", "columns", "sample_rows", "violation_types", "statuses"])
    llm = GoogleGenAIChatGenerator()
    converter = MDconverter()

    # New: prompt để giải thích kết quả + LLM riêng cho phần giải thích
    explain_template = """
    Hãy giải thích ngắn gọn kết quả cho câu hỏi của người dùng.
    Câu hỏi: {{question}}

    SQL đã chạy:
    ```sql
    {{query[0]}}
    ```

    Kết quả thô:
    {{result[0]}}

    Trả lời ngắn gọn, trực tiếp, không nêu chi tiết kỹ thuật.
    """
    explain_prompt = ChatPromptBuilder(
        template=[ChatMessage.from_user(explain_template)],
        required_variables=["question", "query", "result"],
    )
    llm_explainer = GoogleGenAIChatGenerator()

    routes = [
        {
            "condition": "{{'no_answer' not in str_queries[0].lower()}}",
            "output": "{{[str_queries[0]]}}",
            "output_name": "sql",
            "output_type": list[str],
        },
        {
            "condition": "{{'no_answer' in str_queries[0].lower()}}",
            "output": "I cannot answer this question based on the available data. The database contains information about violations with columns for id, employee_name, violation_type, violation_date, and status. Please try asking a question related to these fields.",
            "output_name": "no_answer",
            "output_type": str,
        },
    ]
    router = ConditionalRouter(routes)

    sql_pipeline = Pipeline()
    sql_pipeline.add_component('prompt', prompt)
    sql_pipeline.add_component('llm', llm)
    sql_pipeline.add_component('converter', converter)
    sql_pipeline.add_component('router', router)
    sql_pipeline.add_component('sql_querier', sql_query)

    # New components for explain
    sql_pipeline.add_component('explain_prompt', explain_prompt)
    sql_pipeline.add_component('llm_explainer', llm_explainer)

    sql_pipeline.connect("prompt.prompt", "llm.messages")
    sql_pipeline.connect("llm.replies", "converter.md_queries")
    sql_pipeline.connect("converter.str_queries", "router.str_queries")
    sql_pipeline.connect("router.sql", "sql_querier.sql_queries")

    # New connections to build explanation
    sql_pipeline.connect("sql_querier.results", "explain_prompt.result")
    sql_pipeline.connect("sql_querier.queries", "explain_prompt.query")
    sql_pipeline.connect("explain_prompt.prompt", "llm_explainer.messages")

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
                # Initialize pipeline
                sql_pipeline = setup_pipeline()
                
                # Lấy ngữ cảnh database trước khi chạy pipeline
                db_context = get_db_context()

                # Chạy pipeline với câu hỏi của người dùng và ngữ cảnh mới
                result = sql_pipeline.run({
                    "prompt": {
                        "question": user_question, 
                        **db_context
                    },
                    "explain_prompt": {"question": user_question},
                }, include_outputs_from= ["llm_explainer", "sql_querier", "llm", "prompt", "router"])

                st.session_state.last_result = result

                if "no_answer" in result["router"]:
                    st.warning(result["router"]["no_answer"])
                elif result["llm_explainer"]["replies"]:
                    explanation = result['llm_explainer']['replies'][0].text
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
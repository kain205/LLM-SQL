from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, unquote

load_dotenv()

class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

vn = MyVanna(config={'model': 'hf.co/mradermacher/natural-sql-7b-i1-GGUF:Q4_K_M'})

# parse DATABASE_URL from .env and use it; fallback to explicit literals if missing
db_url = os.getenv("DATABASE_URL")
if db_url:
    p = urlparse(db_url)
    host = p.hostname
    port = p.port or 5432
    user = p.username
    password = unquote(p.password) if p.password else None
    dbname = p.path.lstrip('/') if p.path else None

vn.connect_to_postgres(
    host=host,
    dbname=dbname,
    user=user,
    password=password,
    port=port
)

df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
plan = vn.get_training_plan_generic(df_information_schema)
print(plan)
vn.train(plan = plan)

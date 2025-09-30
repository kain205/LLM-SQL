import os
import json
from haystack import Document
from haystack.utils import Secret
from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the document store, ensuring it can store metadata
document_store = PgvectorDocumentStore(
    connection_string=Secret.from_env_var("DATABASE_URL"),
    embedding_dimension=384,
    recreate_table=True, # Deletes and recreates the table on each run
    table_name="haystack_documents_v2" # Use a new table name
)

def get_indexing_pipeline(doc_store: PgvectorDocumentStore):
    """
    Creates a Haystack pipeline that embeds and writes documents with metadata.
    """
    embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    writer = DocumentWriter(document_store=doc_store)

    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component("embedder", embedder)
    indexing_pipeline.add_component("writer", writer)

    indexing_pipeline.connect("embedder.documents", "writer.documents")
    return indexing_pipeline

def run_indexing(pipeline: Pipeline, knowledge_base_path="data/knowledge_v2.json"):
    """
    Reads the structured JSON, creates Haystack Documents with metadata,
    and runs the indexing pipeline.
    """
    if not os.path.exists(knowledge_base_path):
        print(f"Error: Knowledge base file not found at '{knowledge_base_path}'")
        return

    with open(knowledge_base_path, "r", encoding="utf-8") as f:
        knowledge_data = json.load(f)

    # Convert each JSON object into a Haystack Document
    haystack_docs = []
    for item in knowledge_data:
        doc = Document(
            id=item["id"],
            content=item["content"],
            meta={
                "type": item["type"],
                "category": item["category"],
                "keywords": item.get("keywords", [])
            }
        )
        haystack_docs.append(doc)

    print(f"Prepared {len(haystack_docs)} documents for indexing...")

    # Run the pipeline
    pipeline.run({"embedder": {"documents": haystack_docs}})
    
    print(f"Indexing complete. Document store now contains {len(document_store.filter_documents())} documents.")

if __name__ == "__main__":
    indexing_pipeline = get_indexing_pipeline(doc_store=document_store)
    run_indexing(indexing_pipeline)

    # (Optional) Inspect a document to see the result
    docs = document_store.filter_documents(filters={"field": "meta.id", "operator": "==", "value": "temporal_mapping_002"})
    if docs:
        print("\n--- Sample of an embedded document from the database ---")
        print(f"Content: {docs[0].content}")
        print(f"Metadata: {docs[0].meta}")
        print(f"Embedding vector length: {len(docs[0].embedding)}")
        print("------------------------------------------------------")
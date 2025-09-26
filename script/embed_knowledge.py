from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack import Document
from haystack.utils import Secret
from dotenv import load_dotenv
import os
from haystack import Pipeline
from haystack.components.converters import MarkdownToDocument
from haystack.components.writers import DocumentWriter
from haystack.components.preprocessors import RecursiveDocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder

# Load environment variables
load_dotenv()

# Initialize the persistent document store using PGVector
# This will store the embedded knowledge base in your PostgreSQL database
document_store = PgvectorDocumentStore(
    connection_string=Secret.from_env_var("DATABASE_URL"),
    embedding_dimension=384,  
    vector_function="cosine_similarity",
    recreate_table=True,  # Deletes and recreates the table on each run
    search_strategy="hnsw"
)

def get_indexing_pipeline(doc_store: PgvectorDocumentStore):
    """
    Creates and returns a Haystack pipeline that:
    1. Converts a Markdown file into Haystack Documents.
    2. Cleans up and splits the documents for better embedding.
    3. Creates vector embeddings for each document.
    4. Writes the embedded documents to the specified PGVector document store.
    """

    # Cleans up and splits the Markdown documents
    preprocessor = RecursiveDocumentSplitter(
        separators=["---", "### "],
        split_length=100,
    )

    # Uses a Sentence-Transformers model to create vector embeddings
    embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    
    # Writes the embedded documents into the document store
    writer = DocumentWriter(document_store=doc_store)

    # Build the pipeline
    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component("preprocessor", preprocessor)
    indexing_pipeline.add_component("embedder", embedder)
    indexing_pipeline.add_component("writer", writer)

    # Connect the components in order
    indexing_pipeline.connect("preprocessor.documents", "embedder.documents")
    indexing_pipeline.connect("embedder.documents", "writer.documents")
    
    return indexing_pipeline

def run_indexing(pipeline: Pipeline, knowledge_base_path="data/knowledge.txt"):
    """
    Runs the indexing pipeline on the specified knowledge base file.
    """
    if not os.path.exists(knowledge_base_path):
        print(f"Error: Knowledge base file not found at '{knowledge_base_path}'")
        return
    with open(knowledge_base_path, "r", encoding="utf-8") as f:
        text = f.read()
        doc = Document(content= text)

    print(f"Running indexing on '{knowledge_base_path}'...")
    # The pipeline expects a dictionary mapping component names to their inputs
    pipeline.run({"preprocessor": {"documents": [doc]}})
    
    print(f"Indexing complete. Document store now contains {len(document_store.filter_documents())} documents.")

if __name__ == "__main__":
    # 1. Create the pipeline with our persistent document store
    indexing_pipeline = get_indexing_pipeline(doc_store=document_store)
    
    # 2. Run the pipeline to embed the knowledge.md file and save to the database
    run_indexing(indexing_pipeline)

    # 3. (Optional) Inspect the first document to see the result from the database
    docs = document_store.filter_documents()
    if docs:
        print("\n--- Sample of an embedded document from the database ---")
        print(docs[0].content)
        print(f"Embedding vector length: {len(docs[0].embedding)}")
        print("------------------------------------------------------")

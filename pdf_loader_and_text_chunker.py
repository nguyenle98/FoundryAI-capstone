# REMEMBER TO GET EXTRA POINTS FOR ADVANCED TOKEN BASED CHUNKING METHOD 
'''This script loads a PDF, chunks the text into manageable pieces, embeds them using OpenAI's API, 
and uploads them to Pinecone for vector storage.'''

import pymupdf  # for PDF loading
import tiktoken  # for token-based splitting
import openai
from pinecone import Pinecone, ServerlessSpec
import uuid
from dotenv import load_dotenv
import os

# === CONFIGURATION ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # e.g., "us-east-1-aws"
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

PDF_PATH = "forex_analysis.pdf"
EMBEDDING_MODEL = "text-embedding-3-small"

MAX_TOKENS = 100
OVERLAP = 10


# === Initialize APIs ===
openai.api_key = OPENAI_API_KEY
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# === Helper: Token-based Chunker ===
def token_count_splitter(text, max_tokens=100, overlap=10):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk = enc.decode(tokens[start:end])
        chunks.append(chunk.strip())
        start += max_tokens - overlap
    return chunks


# === Main Workflow ===
def embed_pdf_to_pinecone(pdf_path):
    # 1. Load PDF text
    doc = pymupdf.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)

    # 2. Chunk text
    chunks = token_count_splitter(full_text, MAX_TOKENS, OVERLAP)

    # 3. Embed & upsert
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue

        print(f"Embedding chunk {i+1}/{len(chunks)}...")

        # Embed chunk
        try:
            response = openai.embeddings.create(
                input=chunk,
                model=EMBEDDING_MODEL
            )
            vector = response.data[0].embedding
        except Exception as e:
            print(f"⚠️ Embedding failed: {e}")
            continue

        # Upsert to Pinecone
        try:
            vector_id = f"chunk-{uuid.uuid4()}"
            metadata = {
                "text": chunk,
                "source": "forex_analysis.pdf",
                "chunk_index": i + 1
            }
            index.upsert([(vector_id, vector, metadata)])
        except Exception as e:
            print(f"⚠️ Upsert failed: {e}")

    print("✅ All chunks embedded and uploaded to Pinecone.")


# === Run ===
if __name__ == "__main__":
    embed_pdf_to_pinecone(PDF_PATH)
    stats = index.describe_index_stats()
    print("Index stats:", stats)

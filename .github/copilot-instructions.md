# Copilot Instructions for FoundryAI-capstone

## Project Overview
This project processes financial PDFs, generates embeddings, and stores them in a vector database for AI-powered retrieval and analysis. It integrates with Snowflake for data extraction and Pinecone for vector storage.

## Key Components
- **PDF Processing:**
  - `snowflake_pdf.py`: Connects to Snowflake, queries `fx_analysis`, and generates a formatted PDF (`forex_analysis.pdf`).
  - `pdf_loader_and_text_chunker.py`: Loads PDFs and splits text into chunks using sentence or token-based strategies.
  - `pdf_chuking.py`: Reads the PDF, chunks text, generates OpenAI embeddings, and upserts them into Pinecone.

- **Vector Database Integration:**
  - Uses Pinecone for storing and retrieving vector embeddings.
  - Embeddings are generated via OpenAI's `text-embedding-3-small` model.

- **Secrets Management:**
  - All credentials (Snowflake, OpenAI, Pinecone) must be loaded from environment variables via a `.env` file. Never hardcode secrets.
  - Add `.env` to `.gitignore` to prevent accidental commits.

## Developer Workflow
- **Environment Setup:**
  - Use a virtual environment (e.g., `.venv` or `m03w01`).
  - Install dependencies with `uv pip install -r requirements.txt` or `uv pip install <package>`.
- **Running Scripts:**
  - Activate your environment: `.\.venv\Scripts\activate` or `.\m03w01\Scripts\activate`.
  - Run scripts from the terminal, not the VS Code "Run Code" button, to ensure correct interpreter usage.
- **PDF to Embedding Pipeline:**
  - Generate PDF from Snowflake: `python snowflake_pdf.py`
  - Chunk and embed: `python pdf_chuking.py`

## Patterns & Conventions
- **Chunking:**
  - Use `RecursiveCharacterTextSplitter` for sentence-based splitting.
  - Use `tiktoken` for token-based splitting.
- **Embedding & Upsert:**
  - Each chunk is embedded and upserted into Pinecone with a UUID key and original text metadata.
- **Error Handling:**
  - Minimal error handling; add logging or try/except as needed for production.

## External Dependencies
- `openai`, `pinecone`, `PyPDF2`, `python-dotenv`, `snowflake-connector-python`, `reportlab`, `tiktoken`, `langchain-text-splitters`

## Example: Embedding and Upserting Chunks
```python
for i, chunk in enumerate(chunks):
    if not chunk.strip():
        continue
    response = openai.Embedding.create(input=chunk, model="text-embedding-3-small")
    vector = response['data'][0]['embedding']
    index.upsert([(f"chunk-{uuid.uuid4()}", vector, {"text": chunk})])
```

## Feedback
If any section is unclear or missing, please provide feedback to improve these instructions.

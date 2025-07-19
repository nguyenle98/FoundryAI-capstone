from typing import List, Dict
import PyPDF2
import duckdb
import uuid
from langchain_community.embeddings import HuggingFaceEmbeddings
from rich.console import Console

# Initialize rich console
console = Console()

# Constants
TOP_K_RESULTS = 2
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

# Global variables for tool access
_embeddings = None
_conn = None

def initialize_duckdb():
    """Initialize DuckDB connection and create embeddings table if it doesn't exist."""
    conn = duckdb.connect('pdf_rag_demo.db')
    
    # Create table with array type for embeddings (384 dimensions for all-MiniLM-L6-v2)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_embeddings (
            id VARCHAR PRIMARY KEY,
            text VARCHAR,
            embedding FLOAT[384],
            page_number INTEGER
        )
    """)
    return conn

def read_pdf(file_path: str) -> List[Dict]:
    """Read and extract text from a PDF file, returning chunks with page numbers."""
    try:
        console.print("\n[bold blue]📄 Starting PDF Processing[/bold blue]")
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            console.print(f"[yellow]Found {total_pages} pages in the PDF[/yellow]")
            
            chunks = []
            for page_num, page in enumerate(pdf_reader.pages):
                console.print(f"[cyan]Processing page {page_num + 1}/{total_pages}...[/cyan]")
                text = page.extract_text()
                
                # Split text by periods (because I know my pdf, cheeky move 🤷‍♂️)
                sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
                console.print(f"[yellow]Found {len(sentences)} sentences on page {page_num + 1}[/yellow]")
                
                # Process each sentence
                for sent_num, sentence in enumerate(sentences):
                    # Skip very short sentences (likely headers or footers)
                    if len(sentence) < 20:  # Minimum 20 characters
                        continue
                        
                    # Create a chunk for each sentence
                    chunks.append({
                        'text': sentence,
                        'page_number': page_num + 1,
                        'sentence_number': sent_num + 1
                    })
                    console.print(f"[green]✓ Processed sentence {sent_num + 1} on page {page_num + 1}[/green]")
                
                console.print(f"[green]✓ Page {page_num + 1} processed[/green]")
            
            console.print(f"[bold green]✅ PDF Processing Complete![/bold green]")
            console.print(f"[yellow]Total chunks created: {len(chunks)}[/yellow]")
            return chunks
    except Exception as e:
        console.print(f"[red]❌ Error reading PDF: {str(e)}[/red]")
        return []

def store_pdf_chunks(conn, chunks: List[Dict], embeddings):
    """Store PDF chunks and their embeddings in DuckDB."""
    total_chunks = len(chunks)
    console.print(f"\n[bold blue]🔄 Starting to process {total_chunks} chunks[/bold blue]")
    
    # Create a progress bar
    with console.status("[bold green]Processing chunks...") as status:
        for i, chunk in enumerate(chunks, 1):
            status.update(f"[cyan]Processing chunk {i}/{total_chunks} (Page {chunk['page_number']})[/cyan]")
            
            # Generate embedding for the chunk
            console.print(f"[yellow]Generating embedding for page {chunk['page_number']}...[/yellow]")
            embedding = embeddings.embed_query(chunk['text'])
            console.print(f"[green]✓ Embedding generated[/green]")
            
            # Generate unique ID
            chunk_id = str(uuid.uuid4())
            
            # Insert into DuckDB
            console.print(f"[yellow]Storing chunk in database...[/yellow]")
            conn.execute("""
                INSERT INTO pdf_embeddings (id, text, embedding, page_number)
                VALUES (?, ?, ?, ?)
            """, [chunk_id, chunk['text'], embedding, chunk['page_number']])
            console.print(f"[green]✓ Chunk stored successfully[/green]")
            
            # Update progress
            progress = (i / total_chunks) * 100
            console.print(f"[blue]Progress: {progress:.1f}%[/blue]")
    
    console.print(f"[bold green]✅ All {total_chunks} chunks processed and stored successfully![/bold green]")

def initialize_embeddings():
    """Initialize the embeddings model."""
    global _embeddings
    _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings

def initialize_connection():
    """Initialize the database connection."""
    global _conn
    _conn = initialize_duckdb()
    return _conn

def get_embeddings():
    """Get the embeddings model instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = initialize_embeddings()
    return _embeddings

def get_connection():
    try:
        print("DEBUG: Entering get_connection()")
        conn = duckdb.connect('pdf_rag_demo.db')
        print("DEBUG: DuckDB connection established")
        # Optionally, check if table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pdf_embeddings (
                id VARCHAR PRIMARY KEY,
                text VARCHAR,
                embedding FLOAT[384],
                page_number INTEGER
            )
        """)
        print("DEBUG: pdf_embeddings table checked/created")
        return conn
    except Exception as e:
        print(f"ERROR in get_connection: {e}")
        raise
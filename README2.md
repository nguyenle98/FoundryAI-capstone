# PDF RAG Chatbot

A Retrieval Augmented Generation (RAG) chatbot that can answer questions based on PDF content. The chatbot uses intelligent tool-based RAG to search through PDF documents and provide context-aware responses.

## Features

- **PDF text extraction and chunking** with sentence-level processing
- **Vector similarity search** using HuggingFace embeddings (all-MiniLM-L6-v2)
- **DuckDB storage** for efficient vector storage and retrieval
- **Tool-based RAG implementation** with LangGraph
- **Lazy loading** of embedding models for optimal performance
- **Smart caching** to avoid re-processing existing PDFs
- **Rich console interface** with beautiful formatting and progress indicators
- **Conversation memory** with thread-based management
- **Flexible PDF management** - reuse existing embeddings or add new PDFs

## Architecture

The project consists of two main components:

1. **`pdf_utils.py`**: Core utility functions for:
   - PDF processing and sentence-level chunking
   - Database operations with DuckDB
   - Embeddings management with global caching
   - Resource initialization and connection management

2. **`manual_pdf_rag_chatbot.py`**: Main chatbot implementation with:
   - Tool-based RAG workflow using LangGraph
   - Intelligent conversation management
   - Rich user interface with progress tracking
   - LiteLLM integration for model access

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

## Usage

1. **Run the chatbot**:
   ```bash
   python manual_pdf_rag_chatbot.py
   ```

2. **PDF Management**:
   - If existing embeddings are found, you'll be prompted to either:
     - Use existing embeddings (skip PDF processing)
     - Add a new PDF and replace existing embeddings
   - If no existing embeddings, you'll be prompted for a PDF path

3. **Start chatting!** The chatbot will:
   - Process and store PDF content (if needed)
   - Create embeddings for efficient search
   - Use RAG to find relevant PDF content for your questions

## Sample Prompts

The chatbot demonstrates intelligent behavior based on the query:

### PDF-Specific Queries:
```
tell me about quantum cat
```
- Triggers the search tool automatically
- Searches for relevant content in the PDF
- Provides answer based on PDF content only

### General Knowledge Queries:
```
what is the weather like today?
```
- No tool call is triggered
- Model answers using its own knowledge
- Faster response for non-PDF questions

## Available Commands

- `help`: Show help message with available commands
- `quit` or `exit`: Exit the chatbot gracefully
- `clear`: Clear conversation history and start new thread
- `model`: Show current model information

## How It Works

### 1. **Smart Initialization**:
   - Checks for existing PDF embeddings in database
   - Prompts user for PDF management choice
   - Loads embedding model only when needed (lazy loading)

### 2. **PDF Processing Pipeline**:
   - Extracts text from PDF page by page
   - Splits into sentence-level chunks
   - Generates embeddings for each chunk
   - Stores in DuckDB with page numbers for context

### 3. **Intelligent Query Processing**:
   - Analyzes user query with strong system prompts
   - Automatically decides whether to use PDF search tool
   - If tool is called: searches for relevant chunks using vector similarity
   - If no tool call: answers directly using model knowledge

### 4. **Tool-Based RAG**:
   - Uses `search_similar_chunks` tool for PDF retrieval
   - Returns top 2 most similar chunks by default
   - Provides context-aware responses based on PDF content
   - Maintains conversation context across interactions

## Technical Details

- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **LLM**: GPT-3.5-turbo via LiteLLM
- **Database**: DuckDB with vector similarity support
- **Vector Similarity**: Cosine similarity for chunk retrieval
- **Top K Results**: 2 most relevant chunks (configurable)
- **Chunking Strategy**: Sentence-level with minimum 20 character filter
- **Memory Management**: Thread-based conversation memory

## Performance Optimizations

- **Lazy Loading**: Embedding model only loaded when needed
- **Global Caching**: Embeddings model cached globally to avoid re-loading
- **Smart PDF Management**: Reuses existing embeddings when possible
- **Efficient Storage**: DuckDB provides fast vector similarity search
- **Progress Tracking**: Real-time feedback during PDF processing

## Notes

- **API Key Required**: OpenAI API key must be set in environment
- **Processing Time**: PDF processing depends on file size and content
- **Memory Usage**: Embeddings are cached globally for efficiency
- **Database**: Uses local DuckDB file (`pdf_rag_demo.db`)
- **Thread Safety**: Each conversation gets a unique thread ID
- **Tool Transparency**: All tool calls and search results are logged

## File Structure

```
simple_rag_pdf_chatbot/
├── manual_pdf_rag_chatbot.py  # Main chatbot implementation
├── pdf_utils.py               # PDF processing and utility functions
├── README.md                  # This documentation
├── source/                    # Sample PDF files
└── pdf_rag_demo.db           # DuckDB database (created automatically)
```

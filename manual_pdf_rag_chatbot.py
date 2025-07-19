from dotenv import load_dotenv
import os
from typing import List, Dict
import duckdb
import uuid
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import MessagesState
from langchain_core.tools import tool
from pdf_utils import (
    TOP_K_RESULTS,
    read_pdf, store_pdf_chunks, get_embeddings, get_connection
)

### Extra beauty fancy stuff
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

MODEL_NAME = "gpt-3.5-turbo"

# Initialize rich console
console = Console()

# Load environment variables
load_dotenv()

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Constants
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

@tool
def search_similar_chunks(query: str) -> List[Dict]:
    """Search for similar chunks in the PDF using vector similarity.
    Use this tool when you need to find relevant information from the PDF to answer a question.
    The tool will return the most similar chunks with their page numbers and similarity scores."""
    # Load embeddings on-demand (cached globally)
    embeddings = get_embeddings()
    conn = get_connection()
    
    console.print("\n[bold blue]🔍 Starting similarity search[/bold blue]")
    console.print(f"[cyan]Search query: '{query}'[/cyan]")
    
    # Generate embedding for query
    console.print("[yellow]Generating query embedding...[/yellow]")
    query_embedding = embeddings.embed_query(query)
    console.print("[green]✓ Query embedding generated[/green]")
    
    # Search using cosine similarity
    console.print("[yellow]Searching database for similar chunks...[/yellow]")
    results = conn.execute("""
        SELECT 
            id,
            text,
            page_number,
            array_cosine_similarity(embedding, ?::FLOAT[384]) as similarity
        FROM pdf_embeddings
        ORDER BY similarity DESC
        LIMIT ?
    """, [query_embedding, TOP_K_RESULTS]).fetchall()
    console.print(f"[green]✓ Found {len(results)} similar chunks[/green]")
    
    # Convert results to list of dictionaries
    return [
        {
            'id': row[0],
            'fields': {
                'chunk_text': row[1],
                'page_number': row[2]
            },
            'score': row[3]
        }
        for row in results
    ]

def create_rag_chatbot(model: str = MODEL_NAME):
    """Create a RAG-enabled chatbot instance using LangGraph and LiteLLM"""
    console.print("\n[bold blue]🤖 Initializing RAG Chatbot[/bold blue]")
    
    # Initialize DuckDB connection only
    console.print("[yellow]Initializing DuckDB connection...[/yellow]")
    conn = get_connection()
    console.print("[green]✓ DuckDB connection established[/green]")
    
    # Initialize the LLM
    console.print("[yellow]Initializing language model...[/yellow]")
    llm = ChatLiteLLM(
        model=model,
        temperature=0.7
    )
    console.print("[green]✓ Language model initialized[/green]")
    
    # Create the workflow
    console.print("[yellow]Setting up conversation workflow...[/yellow]")
    workflow = StateGraph(state_schema=MessagesState)
    
    # Define the RAG node
    def rag_node(state: MessagesState):
        """Process the query through RAG pipeline"""
        # Get the last message (user query)
        last_message = state["messages"][-1]
        
        # Bind the search tool to the LLM
        augmented_llm = llm.bind_tools([search_similar_chunks])
        
        # Create initial messages with stronger instruction to use the tool
        messages = [
            SystemMessage(content="""You are a helpful AI assistant with access to a PDF document. 
IMPORTANT: ALWAYS use the search_similar_chunks tool to find relevant information from the PDF before answering any question.
Do not rely on your own knowledge - only use information found in the PDF through the search tool.
If the search doesn't find relevant information, clearly state that the information is not available in the PDF."""),
            last_message
        ]
        
        # Get initial response from model
        console.print("\n[bold blue]🤖 Processing user query...[/bold blue]")
        response = augmented_llm.invoke(messages)
        
        # Check for tool calls
        if response.tool_calls:
            console.print("\n[bold yellow]🔧 Tool Call Detected[/bold yellow]")
            console.print("[cyan]The model decided to search the PDF for relevant information.[/cyan]")
            tool_messages = []
            for tool_call in response.tool_calls:
                function_name = tool_call["name"]
                arguments = tool_call["args"]
                
                console.print(f"\n[yellow]📝 Tool Details:[/yellow]")
                console.print(f"[cyan]Function: {function_name}[/cyan]")
                console.print(f"[cyan]Query: {arguments['query']}[/cyan]")
                
                if function_name == "search_similar_chunks":
                    # Execute the search tool
                    similar_chunks = search_similar_chunks.invoke(arguments["query"])
                    
                    # Create context from similar chunks
                    context = "\n".join([
                        f"Page {chunk['fields']['page_number']}: {chunk['fields']['chunk_text']}"
                        for chunk in similar_chunks
                    ])
                    
                    # Log the RAG search results
                    console.print("\n[bold blue]📊 RAG Search Results:[/bold blue]")
                    for chunk in similar_chunks:
                        console.print(f"[cyan]Score: {chunk['score']:.3f}[/cyan]")
                        console.print(f"[yellow]Page: {chunk['fields']['page_number']}[/yellow]")
                        console.print(f"[green]Text: {chunk['fields']['chunk_text'][:200]}...[/green] ")
                    
                    # Create tool message with context
                    tool_messages.append(ToolMessage(
                        content=f"Here is the relevant information from the PDF:\n\n{context}",
                        tool_call_id=tool_call["id"]
                    ))
            
            # Get final response with tool results
            console.print("\n[bold blue]🤖 Generating final response with PDF context...[/bold blue]")
            final_messages = [
                SystemMessage(content="""You are a helpful AI assistant. Use ONLY the provided context from the PDF to answer the question.
Do not use any external knowledge or information not found in the PDF context.
If the context doesn't contain enough information to answer the question, clearly state that the information is not available in the PDF.
Base your response entirely on the PDF content provided."""),
                last_message,
                response
            ] + tool_messages
            
            final_response = augmented_llm.invoke(final_messages)
            return {"messages": final_response}
        else:
            # No tool call needed, return the initial response
            console.print("\n[bold green]✓ No PDF search needed - answering directly[/bold green]")
            return {"messages": response}
    
    # Add the RAG node
    workflow.add_node("rag", rag_node)
    
    # Add edges
    workflow.add_edge(START, "rag")
    workflow.add_edge("rag", END)
    
    # Compile the workflow with memory
    console.print("[yellow]Compiling workflow...[/yellow]")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    console.print("[green]✓ Workflow compiled successfully[/green]")
    
    console.print("[bold green]✅ RAG Chatbot initialization complete![/bold green]")
    return app, conn

def clear_conversation(conversation):
    """Clear the conversation history"""
    conversation, _ = create_rag_chatbot()
    console.print("[yellow]Conversation history cleared![/yellow]")
    return conversation

def display_help():
    """Display help information"""
    help_text = """
    Available Commands:
    • help - Show this help message
    • quit or exit - Exit the chatbot
    • clear - Clear conversation history
    • model - Show current model
    
    The chatbot uses RAG (Retrieval Augmented Generation) to search through your PDF
    and provide context-aware responses. Each response is based on the most relevant
    sections found in the PDF.
    """
    console.print(Panel(help_text, title="Help", border_style="cyan"))

def main():
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        console.print("[red]❌ Error: Please set your OPENAI_API_KEY environment variable[/red]")
        return
    
    # Create chatbot instance and get database connection first
    conversation, conn = create_rag_chatbot()
    
    # Check if PDF content is already processed
    console.print("\n[bold blue]📚 Checking PDF Processing Status[/bold blue]")
    existing_count = conn.execute("SELECT COUNT(*) FROM pdf_embeddings").fetchone()[0]
    
    if existing_count > 0:
        console.print(f"[green]✓ Found {existing_count} existing PDF embeddings in database[/green]")        
        # Ask user if they want to re-process the PDF
        while True:
            user_choice = input("Do you want to add a new PDF and replace the existing one? (y/n): ").strip().lower()
            if user_choice in ['y', 'yes']:
                console.print("[yellow]You chose to re-process the PDF.[/yellow]")
                break
            elif user_choice in ['n', 'no']:
                console.print("[green]✓ Using existing embeddings[/green]")
                # Skip PDF processing and go directly to chat
                start_chat_session(conversation)
                return
            else:
                console.print("[red]Please enter 'y' or 'n'[/red]")
    
    # Get PDF path from user (only if re-processing or no existing data)
    console.print("\n[bold blue]📂 PDF Input[/bold blue]")
    pdf_path = input("Please enter the path to your PDF file: ").strip()
    if not os.path.exists(pdf_path):
        console.print("[red]❌ Error: PDF file not found![/red]")
        return
    
    # Process PDF based on user choice or if no existing data
    if existing_count > 0:
        # User chose to re-process
        console.print("[yellow]Clearing existing embeddings and re-processing PDF...[/yellow]")
        conn.execute("DELETE FROM pdf_embeddings")
        console.print("[green]✓ Existing embeddings cleared[/green]")
    
    # Load embeddings model only when needed for PDF processing
    console.print("[yellow]Loading embeddings model for PDF processing...[/yellow]")
    embeddings = get_embeddings()
    console.print("[green]✓ Embeddings model loaded[/green]")
    
    # Read and store PDF content
    console.print("\n[bold blue]📚 PDF Processing Pipeline[/bold blue]")
    chunks = read_pdf(pdf_path)
    store_pdf_chunks(conn, chunks, embeddings)
    
    # Start chat session
    start_chat_session(conversation)

def start_chat_session(conversation):
    """Start the chat session with the user."""
    # Generate a unique thread ID for this conversation
    current_thread_id = str(uuid.uuid4())
    
    # Welcome message
    console.print("\n[bold blue]🤖 Starting Chat Session[/bold blue]")
    console.print(Panel(
        Text("PDF RAG Assistant", style="bold cyan"),
        border_style="cyan"
    ))
    console.print("[yellow]This chatbot uses RAG to search through your PDF and provide context-aware responses.[/yellow]")
    console.print(f"[yellow]Current Thread ID: {current_thread_id}[/yellow]")
    console.print("[yellow]Type 'help' for available commands[/yellow]")
    
    while True:
        try:
            # Get user input
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit']:
                console.print("\n[green]👋 Goodbye! Have a great day![/green]")
                break
            elif user_input.lower() == 'clear':
                conversation = clear_conversation(conversation)
                current_thread_id = str(uuid.uuid4())
                console.print(f"[yellow]🔄 New Thread ID: {current_thread_id}[/yellow]")
                continue
            elif user_input.lower() == 'model':
                console.print(Panel(
                    f"Current model: {MODEL_NAME}",
                    title="Model Info",
                    border_style="yellow"
                ))
                continue
            elif user_input.lower() == 'help':
                display_help()
                continue
            
            # Create input message
            input_messages = [HumanMessage(content=user_input)]
            
            # Get response from the model with thread ID for memory
            console.print("[yellow]Processing your question...[/yellow]")
            result = conversation.invoke(
                {"messages": input_messages},
                config={"configurable": {"thread_id": current_thread_id}}
            )

            # Print the response
            if result and "messages" in result and result["messages"]:
                console.print("\n[bold green]Assistant:[/bold green]")
                console.print(Markdown(result['messages'][-1].content))
                
        except KeyboardInterrupt:
            console.print("\n\n[green]👋 Goodbye! Have a great day![/green]")
            break
        except Exception as e:
            console.print(f"\n[red]❌ An error occurred: {str(e)}[/red]")
            console.print("[yellow]Please try again or type 'quit' to exit[/yellow]")

if __name__ == "__main__":
    main()

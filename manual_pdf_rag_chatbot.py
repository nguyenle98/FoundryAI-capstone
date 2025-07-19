from dotenv import load_dotenv
import os
from typing import List, Dict
import duckdb
import snowflake.connector
import uuid
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
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

def validate_snowflake_connection():
    """Connect to Snowflake, show schema info, and validate access."""
    console.print("\n[bold blue]🔗 Connecting to Snowflake and validating access...[/bold blue]")
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )
        cur = conn.cursor()
        # Show available tables
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        if tables:
            console.print("[green]✅ Tables in schema:[/green]")
            for t in tables:
                console.print(f"  - [cyan]{t[1]}[/cyan]")  # t[1] is table name
        else:
            console.print("[yellow]⚠️ No tables found in schema.[/yellow]")

        # Show columns for a key table (replace with your table name if needed)
        try:
            cur.execute("DESC TABLE MART_EXCHANGE_RATES")
            columns = cur.fetchall()
            console.print("[green]✅ Columns in MART_EXCHANGE_RATES:[/green]")
            for c in columns:
                console.print(f"  - [magenta]{c[0]}[/magenta] ({c[1]})")  # c[0]=column name, c[1]=type
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not describe MART_EXCHANGE_RATES: {e}[/yellow]")

        # Validate access with a simple query
        try:
            cur.execute("SELECT COUNT(*) FROM MART_EXCHANGE_RATES")
            count = cur.fetchone()[0]
            console.print(f"[green]✅ Table MART_EXCHANGE_RATES has {count} rows.[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not query MART_EXCHANGE_RATES: {e}[/yellow]")

        cur.close()
        conn.close()
        console.print("[bold green]✅ Snowflake connection and access validated![/bold green]\n")
    except Exception as e:
        console.print(f"[red]❌ Snowflake connection or access failed: {e}[/red]")

def get_conversation_summary(messages: List) -> str:
    """Generate a summary of the current conversation for context awareness"""
    if len(messages) <= 2:  # Just system + current message
        return "This is the beginning of our conversation."
    
    # Create a simple summary of the last few exchanges
    recent_messages = messages[-8:]  # Last 4 exchanges (user + assistant pairs)
    summary_parts = []
    
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            summary_parts.append(f"User: {msg.content[:80]}...")
        elif isinstance(msg, AIMessage) and not isinstance(msg, ToolMessage):
            summary_parts.append(f"Assistant: {msg.content[:80]}...")
    
    return "Recent conversation: " + " | ".join(summary_parts[-4:])  # Last 2 exchanges

def should_use_pdf_search(query: str, conversation_history: List) -> bool:
    """Determine if the query requires PDF search based on content and context"""
    # Keywords that typically require PDF search
    pdf_indicators = [
        'what does', 'according to', 'in the document', 'document says', 
        'pdf states', 'mentioned in', 'find information', 'search for',
        'explain from', 'quote from', 'reference', 'citation'
    ]
    
    # Check if query contains PDF-related keywords
    query_lower = query.lower()
    has_pdf_keywords = any(indicator in query_lower for indicator in pdf_indicators)
    
    # Check recent conversation for PDF context
    recent_context_mentions_pdf = False
    if len(conversation_history) > 1:
        recent_messages = conversation_history[-4:]  # Check last few messages
        for msg in recent_messages:
            if hasattr(msg, 'content') and msg.content:
                if any(indicator in msg.content.lower() for indicator in ['pdf', 'document', 'page']):
                    recent_context_mentions_pdf = True
                    break
    
    return has_pdf_keywords or recent_context_mentions_pdf or len(query) > 20

def create_rag_chatbot(model: str = MODEL_NAME):
    """Create a RAG-enabled chatbot instance using LangGraph and LiteLLM"""
    console.print("\n[bold blue]🤖 Initializing Enhanced RAG Chatbot[/bold blue]")
    
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
    
    # Enhanced RAG node with better context retention
    def rag_node(state: MessagesState):
        """Process the query through RAG pipeline with full context retention"""
        # Get ALL messages from the conversation history
        conversation_messages = state["messages"]
        last_message = conversation_messages[-1]
        
        console.print(f"\n[bold blue]🧠 Processing with {len(conversation_messages)} messages in context[/bold blue]")
        
        # Bind the search tool to the LLM
        augmented_llm = llm.bind_tools([search_similar_chunks])
        
        # Create enhanced system message that preserves context
        system_content = """You are a helpful AI assistant with access to a PDF document. 

CONTEXT AWARENESS:
- Maintain full awareness of our conversation history
- Reference previous questions and answers when relevant
- Build upon previous discussions naturally

PDF SEARCH STRATEGY:
- IMPORTANT: ALWAYS use the search_similar_chunks tool when questions require specific information from the PDF
- Always search before answering factual questions about document content
- Do not rely on your own knowledge - only use information found in the PDF through the search tool.
- If information isn't found in the PDF, then you can use your own knowledge to answer, but always clarify that the information is not from the PDF.

RESPONSE GUIDELINES:
- Be conversational and maintain discussion flow when asked, otherwise be concise and factual from the PDF
- Reference earlier parts of our conversation when helpful
- Provide complete, helpful answers based on available information"""
        
        # Preserve conversation history while ensuring system message is present
        if not conversation_messages or not isinstance(conversation_messages[0], SystemMessage):
            messages_for_llm = [SystemMessage(content=system_content)] + conversation_messages
        else:
            # Update existing system message to include context awareness
            messages_for_llm = [SystemMessage(content=system_content)] + conversation_messages[1:]
        
        # Add conversation summary for better context understanding
        if len(conversation_messages) > 3:
            context_summary = get_conversation_summary(conversation_messages)
            context_msg = SystemMessage(content=f"CONVERSATION CONTEXT: {context_summary}")
            messages_for_llm.insert(1, context_msg)
        
        # Get initial response from model
        console.print("\n[bold blue]🤖 Processing query with full conversation context...[/bold blue]")
        response = augmented_llm.invoke(messages_for_llm)
        
        # Check for tool calls
        if response.tool_calls:
            console.print("\n[bold yellow]🔧 PDF Search Tool Activated[/bold yellow]")
            tool_messages = []
            
            for tool_call in response.tool_calls:
                function_name = tool_call["name"]
                arguments = tool_call["args"]
                
                console.print(f"\n[yellow]📝 Tool Details:[/yellow]")
                console.print(f"[cyan]Function: {function_name}[/cyan]")
                console.print(f"[cyan]Search Query: {arguments['query']}[/cyan]")
                
                if function_name == "search_similar_chunks":
                    # Execute the search tool
                    similar_chunks = search_similar_chunks.invoke(arguments["query"])
                    
                    if similar_chunks:
                        # Create rich context from similar chunks
                        context_parts = []
                        for chunk in similar_chunks:
                            context_parts.append(
                                f"[Page {chunk['fields']['page_number']}] {chunk['fields']['chunk_text']}"
                            )
                        context = "\n\n".join(context_parts)
                        
                        # Log the RAG search results
                        console.print("\n[bold blue]📊 RAG Search Results:[/bold blue]")
                        for i, chunk in enumerate(similar_chunks, 1):
                            console.print(f"[cyan]Result {i} - Score: {chunk['score']:.3f}[/cyan]")
                            console.print(f"[yellow]Page: {chunk['fields']['page_number']}[/yellow]")
                            console.print(f"[green]Preview: {chunk['fields']['chunk_text'][:150]}...[/green]")
                        
                        tool_content = f"Found {len(similar_chunks)} relevant sections from the PDF:\n\n{context}"
                    else:
                        tool_content = "No relevant information found in the PDF for this query."
                        console.print("[yellow]⚠️ No relevant PDF content found[/yellow]")
                    
                    # Create tool message with context
                    tool_messages.append(ToolMessage(
                        content=tool_content,
                        tool_call_id=tool_call["id"]
                    ))
            
            # Generate final response with complete context preservation
            console.print("\n[bold blue]🤖 Generating contextualized response...[/bold blue]")
            
            # Build final message chain preserving everything
            final_messages = messages_for_llm + [response] + tool_messages
            
            final_response = augmented_llm.invoke(final_messages)
            
            # Return complete updated state with all messages
            return {"messages": conversation_messages + [response] + tool_messages + [final_response]}
        else:
            # No tool call needed - direct conversational response
            console.print("\n[bold green]✓ Direct conversational response (no PDF search needed)[/bold green]")
            return {"messages": conversation_messages + [response]}
    
    # Add the enhanced RAG node
    workflow.add_node("rag", rag_node)
    
    # Add edges
    workflow.add_edge(START, "rag")
    workflow.add_edge("rag", END)
    
    # Compile the workflow with memory
    console.print("[yellow]Compiling workflow with enhanced memory management...[/yellow]")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    console.print("[green]✓ Enhanced workflow compiled successfully[/green]")
    
    console.print("[bold green]✅ Enhanced RAG Chatbot initialization complete![/bold green]")
    return app, conn

def clear_conversation(conversation):
    """Clear the conversation history and create a new instance"""
    conversation, _ = create_rag_chatbot()
    console.print("[yellow]🔄 Conversation history cleared! Starting fresh.[/yellow]")
    return conversation

def display_help():
    """Display help information"""
    help_text = """
    🤖 Enhanced PDF RAG Assistant Commands:
    
    • help - Show this help message
    • quit or exit - Exit the chatbot  
    • clear - Clear conversation history and start fresh
    • model - Show current model information
    • context - Show conversation context summary
    • stats - Show database statistics
    
    🧠 Context Features:
    • Maintains full conversation history within each session
    • References previous questions and answers
    • Intelligently decides when to search the PDF
    • Builds upon ongoing discussions naturally
    
    🔍 PDF Search:
    • Automatically searches PDF when you ask specific questions
    • Provides page references for all information
    • Combines PDF content with conversation context
    """
    console.print(Panel(help_text, title="Enhanced PDF RAG Assistant Help", border_style="cyan"))

def show_context_info(conversation, thread_id):
    """Show current conversation context information"""
    try:
        # This is a simplified context display - in a real implementation,
        # you'd retrieve the actual conversation state from the memory
        console.print(Panel(
            f"Thread ID: {thread_id}\nContext: Maintained across conversation\nMemory: Active",
            title="Context Information",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[yellow]Context info unavailable: {str(e)}[/yellow]")

def show_database_stats(conn):
    """Show database statistics"""
    try:
        count = conn.execute("SELECT COUNT(*) FROM pdf_embeddings").fetchone()[0]
        pages = conn.execute("SELECT COUNT(DISTINCT page_number) FROM pdf_embeddings").fetchone()[0]
        console.print(Panel(
            f"Total chunks: {count}\nPages processed: {pages}\nDatabase: pdf_rag_demo.db",
            title="Database Statistics",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]Database stats unavailable: {str(e)}[/red]")

def main():
    """Main function with enhanced error handling and user experience"""
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        console.print("[red]❌ Error: Please set your OPENAI_API_KEY environment variable[/red]")
        console.print("[yellow]💡 Create a .env file with: OPENAI_API_KEY=your_api_key_here[/yellow]")
        return
    
    try:
        # Create chatbot instance and get database connection
        conversation, conn = create_rag_chatbot()
        
        # Check if PDF content is already processed
        console.print("\n[bold blue]📚 Checking PDF Processing Status[/bold blue]")
        existing_count = conn.execute("SELECT COUNT(*) FROM pdf_embeddings").fetchone()[0]
        
        if existing_count > 0:
            console.print(f"[green]✓ Found {existing_count} existing PDF chunks in database[/green]")
            
            # Ask user if they want to re-process the PDF
            while True:
                user_choice = input("Do you want to add a new PDF and replace the existing one? (y/n): ").strip().lower()
                if user_choice in ['y', 'yes']:
                    console.print("[yellow]You chose to re-process the PDF.[/yellow]")
                    break
                elif user_choice in ['n', 'no']:
                    console.print("[green]✓ Using existing PDF embeddings[/green]")
                    # Skip PDF processing and go directly to chat
                    start_enhanced_chat_session(conversation, conn)
                    return
                else:
                    console.print("[red]Please enter 'y' or 'n'[/red]")
        
        # Get PDF path from user (only if re-processing or no existing data)
        console.print("\n[bold blue]📂 PDF Input[/bold blue]")
        while True:
            pdf_path = input("Please enter the path to your PDF file: ").strip()
            if pdf_path.startswith('"') and pdf_path.endswith('"'):
                pdf_path = pdf_path[1:-1]  # Remove quotes if present
            
            if os.path.exists(pdf_path):
                break
            else:
                console.print("[red]❌ Error: PDF file not found! Please check the path and try again.[/red]")
        
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
        console.print("\n[bold blue]📚 Enhanced PDF Processing Pipeline[/bold blue]")
        chunks = read_pdf(pdf_path)
        store_pdf_chunks(conn, chunks, embeddings)
        
        # Validate Snowflake connection and schema
        validate_snowflake_connection()

        # Start enhanced chat session
        start_enhanced_chat_session(conversation, conn)
        
    except KeyboardInterrupt:
        console.print("\n\n[green]👋 Goodbye! Have a great day![/green]")
    except Exception as e:
        console.print(f"\n[red]❌ An error occurred during initialization: {str(e)}[/red]")
        console.print("[yellow]Please check your environment setup and try again.[/yellow]")

def start_enhanced_chat_session(conversation, conn):
    """Start the enhanced chat session with better UX and context management"""
    # Generate a unique thread ID for this conversation
    current_thread_id = str(uuid.uuid4())
    
    # Welcome message
    console.print("\n[bold blue]🤖 Enhanced PDF RAG Assistant[/bold blue]")
    console.print(Panel(
        Text("🧠 Context-Aware • 🔍 PDF-Powered • 💬 Conversational", style="bold cyan"),
        border_style="cyan"
    ))
    console.print("[green]✨ This assistant maintains conversation context and intelligently searches your PDF[/green]")
    console.print(f"[dim]Thread ID: {current_thread_id[:8]}...[/dim]")
    console.print("[yellow]💡 Type 'help' for commands or just start asking questions![/yellow]")
    
    message_count = 0
    
    while True:
        try:
            # Get user input with better prompt
            user_input = console.input(f"\n[bold cyan]You ({message_count + 1}):[/bold cyan] ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['quit', 'exit']:
                console.print("\n[green]👋 Thank you for stopping by! Goodbye![/green]")
                break
            elif user_input.lower() == 'clear':
                conversation = clear_conversation(conversation)
                current_thread_id = str(uuid.uuid4())
                message_count = 0
                console.print(f"[yellow]🔄 New conversation started! Thread ID: {current_thread_id[:8]}...[/yellow]")
                continue
            elif user_input.lower() == 'model':
                console.print(Panel(
                    f"Model: {MODEL_NAME}\nEmbedding Model: {EMBEDDING_MODEL}\nContext: Enhanced with memory",
                    title="Model Information",
                    border_style="yellow"
                ))
                continue
            elif user_input.lower() == 'help':
                display_help()
                continue
            elif user_input.lower() == 'context':
                show_context_info(conversation, current_thread_id)
                continue
            elif user_input.lower() == 'stats':
                show_database_stats(conn)
                continue
            
            # Create input message
            input_messages = [HumanMessage(content=user_input)]
            
            # Get response from the model with thread ID for memory
            console.print("[yellow]🤔 Thinking and searching...[/yellow]")
            result = conversation.invoke(
                {"messages": input_messages},
                config={"configurable": {"thread_id": current_thread_id}}
            )

            # Print the response with enhanced formatting
            if result and "messages" in result and result["messages"]:
                final_message = result['messages'][-1]
                console.print(f"\n[bold green]Assistant ({message_count + 1}):[/bold green]")
                console.print(Markdown(final_message.content))
                message_count += 1
                
                # Show context retention indicator
                if message_count > 1:
                    console.print(f"[dim]💡 Maintaining context from {message_count} previous exchanges[/dim]")
                
        except KeyboardInterrupt:
            console.print("\n\n[green]👋 Session interrupted. Goodbye![/green]")
            break
        except Exception as e:
            console.print(f"\n[red]❌ An error occurred: {str(e)}[/red]")
            console.print("[yellow]💡 Try rephrasing your question or type 'help' for assistance[/yellow]")

if __name__ == "__main__":
    main()
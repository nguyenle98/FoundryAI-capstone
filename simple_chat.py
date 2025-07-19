import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone
import snowflake.connector
import pandas as pd

load_dotenv()

# 1. Setup Pinecone retriever
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENV"))
index = pinecone.Index(os.getenv("PINECONE_INDEX"))
embeddings = OpenAIEmbeddings()
vectorstore = Pinecone(index, embeddings.embed_query, "text")
retriever = vectorstore.as_retriever()

# 2. Setup Snowflake connector
def query_snowflake(sql):
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    df = pd.read_sql(sql, conn)
    conn.close()
    return df.to_string(index=False)

# 3. Setup LLM and memory
llm = ChatOpenAI(temperature=0.7, openai_api_key=os.getenv("OPENAI_API_KEY"))
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
qa = ConversationalRetrievalChain.from_llm(llm, retriever, memory=memory, return_source_documents=True)

# 4. Intent detection (simple version)
def detect_intent(question):
    if "table" in question or "rate" in question or "exchange" in question:
        return "SQL"
    elif "document" in question or "pdf" in question:
        return "RAG"
    else:
        return "CHAT"

# 5. CLI loop
print("Welcome to the Capstone Chatbot! (type 'exit' to quit)")
while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    intent = detect_intent(user_input)
    if intent == "SQL":
        # For demo, use a fixed query or parse from user_input
        sql = "SELECT * FROM DB_SCHEMA.MART_EXCHANGE_RATES LIMIT 5"
        result = query_snowflake(sql)
        print("Bot (Warehouse):\n", result)
    elif intent == "RAG":
        result = qa({"question": user_input})
        print("Bot (PDF):", result["answer"])
        # Optionally print citations: print(result["source_documents"])
    else:
        print("Bot: I'm here to help with your data and documents!")
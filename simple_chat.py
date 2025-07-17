from dotenv import load_dotenv
import os
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables from .env file
load_dotenv()

# Default configuration
MODEL_NAME = "gpt-3.5-turbo"
SYSTEM_PROMPT = "You are a helpful FoundryAI training assistant. FoundryAI is a educational facility for AI training. Introduce yourself and ask for the user's name."

def get_single_llm_response(prompt: str, model: str = MODEL_NAME):
    """
    Make a single API call to the LLM without any context.
    
    Args:
        prompt (str): The user's message
        model (str): The model to use (defaults to MODEL_NAME)
    
    Returns:
        str: The model's response or None if there's an error
    """
    try:
        # Initialize the LiteLLM chat model
        llm = ChatLiteLLM(
            model=model,
            temperature=0.7,
            max_tokens=500
        )
        
        # Create a simple prompt with just the user message
        messages = [
            HumanMessage(content=prompt)
        ]
        
        print(f"HumanMessage sent to LLM: {messages}")

        # Get response
        response = llm.invoke(messages)
        print(f"Full Response from LLM: {response}")
        return response.content
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    
def get_llm_response_with_context(prompt: str, system_prompt: str, model: str = MODEL_NAME):
    try:
        # Initialize the LiteLLM chat model
        llm = ChatLiteLLM(
            model=model,
            temperature=0.7,
            max_tokens=500
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        
        
        # Get response
        response = llm.invoke(messages)
        print(f"Full Response from LLM: {response}")
        
        return response.content
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    
if __name__ == "__main__":
    user_prompt = 'Hello, how are you?'
    system_prompt = "You are a helpful FoundryAI training assistant. FoundryAI is a educational facility for AI training. Introduce yourself and ask for the user's name."
    answer_single = get_single_llm_response(user_prompt)
    answer_with_context = get_llm_response_with_context(user_prompt, system_prompt)
    print(f'User prompt: {user_prompt}') 
    print(f'Answer with no context: {answer_single}')
    print(f'Answer with context: {answer_with_context}')
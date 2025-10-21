"""Generic AI agent script with file access tools supporting Gemini and Ollama."""

import os
from typing import Optional
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from agenttools.tools import get_file_tools


class FileAgent:
    """An AI agent with file access capabilities supporting Gemini and Ollama providers."""
    
    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """Initialize the FileAgent.
        
        Args:
            provider: LLM provider to use ('gemini' or 'ollama')
            model: Specific model name to use (optional, uses defaults from .env)
        """
        load_dotenv()
        
        self.provider = provider.lower()
        self.tools = get_file_tools()
        
        # Initialize the appropriate LLM
        if self.provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
            model_name = model or os.getenv("GEMINI_MODEL", "gemini-pro")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.7
            )
        elif self.provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = model or os.getenv("OLLAMA_MODEL", "llama2")
            self.llm = ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=0.7
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'ollama'")
        
        # Create the agent with system message
        system_message = """You are a helpful AI assistant with access to file system tools.
You can read files, write files, list directories, and check if files exist.
Always be clear about what operations you're performing and their results.
If you encounter errors, explain them clearly to the user."""
        
        self.agent_executor = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=system_message
        )
    
    def run(self, query: str) -> str:
        """Run the agent with a user query.
        
        Args:
            query: The user's query or instruction
            
        Returns:
            The agent's response
        """
        try:
            result = self.agent_executor.invoke({"messages": [HumanMessage(content=query)]})
            # Extract the last message content
            if result and "messages" in result:
                last_message = result["messages"][-1]
                return last_message.content
            return str(result)
        except Exception as e:
            return f"Error executing agent: {str(e)}"
    
    def chat(self):
        """Start an interactive chat session with the agent."""
        print(f"Starting chat with {self.provider.upper()} agent...")
        print("Type 'exit' or 'quit' to end the session.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                response = self.run(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}\n")


def main():
    """Main entry point for the agent script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI agent with file access tools supporting Gemini and Ollama"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "ollama"],
        default=os.getenv("LLM_PROVIDER", "gemini"),
        help="LLM provider to use (default: gemini)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model name to use (optional)"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to execute (if not provided, starts interactive mode)"
    )
    
    args = parser.parse_args()
    
    try:
        agent = FileAgent(provider=args.provider, model=args.model)
        
        if args.query:
            # Single query mode
            response = agent.run(args.query)
            print(response)
        else:
            # Interactive mode
            agent.chat()
    
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

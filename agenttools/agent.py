"""Generic AI agent script with file access tools supporting Gemini and Ollama."""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from agenttools.tools import get_file_tools
from agenttools.formatters import normalize_content

class FileAgent:
    """An AI agent with file access capabilities supporting Gemini and Ollama providers."""

    def __init__(self, provider: str = "gemini", model: Optional[str] = None):
        """Initialize the FileAgent.

        Args:
            provider: LLM provider to use ('gemini' or 'ollama')
            model: Specific model name to use (optional, uses defaults from .env)
        """
        # This will load environment variables from a .env file if present
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
                temperature=0.1,
                top_p=0.8,
                top_k=50,
                max_tokens=4096
            )
        elif self.provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            # keep for error messages
            self.base_url = base_url
            model_name = model or os.getenv("OLLAMA_MODEL", "granite4:micro-h")
            self.llm = ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=0.1,
                top_p=0.8,
                top_k=50,
                max_tokens=4096
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'ollama'")

        # Create the agent with system message
        system_message = (
            "You are a helpful AI assistant with access to file system tools.\n"
            "You can read files, write files, list directories, and check if files exist.\n"
            "Always be clear about what operations you're performing and their results.\n"
            "If you encounter errors, explain them clearly to the user."
        )

        # Use the newer langchain.agents.create_agent API. Pass the system
        # prompt as `system_prompt` to prime the agent's behavior.
        self.agent_executor = create_agent(self.llm, self.tools, system_prompt=system_message)

    def run(self, query: str) -> str:
        """Run the agent with a user query.

        Args:
            query: The user's query or instruction

        Returns:
            The agent's response
        """
        try:
            result = self.agent_executor.invoke({"messages": [HumanMessage(content=query)]})

            # Normalize access to messages whether `result` is a dict or an object
            msgs = None
            if hasattr(result, "messages"):
                try:
                    msgs = list(result.messages)
                except Exception:
                    msgs = result.messages
            elif isinstance(result, dict) and "messages" in result:
                msgs = result["messages"]

            if msgs:
                last = msgs[-1]
                # Message may expose `.content` or be a mapping
                if hasattr(last, "content"):
                    return normalize_content(last.content)
                if isinstance(last, dict) and "content" in last:
                    return normalize_content(last["content"])

            # Nothing matched; return a readable representation
            return normalize_content(result)
        except Exception as e:
            msg = str(e)
            # Provide a helpful hint when the Ollama client cannot connect to the
            # local Ollama server (common when it's not running or wrong URL).
            if self.provider == "ollama" and (
                "Connection refused" in msg or "ConnectError" in msg or "[Errno 111]" in msg
            ):
                base = getattr(self, "base_url", "http://localhost:11434")
                hint = (
                    f"\nHint: The Ollama client could not connect to {base}.\n"
                    "Make sure the Ollama server/daemon is running and that OLLAMA_BASE_URL is set correctly.\n"
                    "You can test connectivity with: curl <base_url>  or check listening ports: ss -ltnp | grep 11434"
                )
                return f"Error executing agent: {msg}{hint}"

            return f"Error executing agent: {msg}"

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
        help="LLM provider to use (default: gemini)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model name to use (optional)",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to execute (if not provided, starts interactive mode)",
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

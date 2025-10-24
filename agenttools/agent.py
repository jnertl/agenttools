"""Generic AI agent script with file access tools supporting Gemini and Ollama."""

import os
import argparse
import json
import re
from typing import Optional
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from agenttools.tools import get_file_tools
from agenttools.formatters import normalize_content
from agenttools.system_prompt import load_system_prompt
import agenttools.tracing as tracing

class FileAgent:
    """An AI agent with file access capabilities supporting Gemini and Ollama providers."""

    def __init__(self, provider: str = None, model: str = None, response_file: str | None = None):
        """Initialize the FileAgent.

        Args:
            provider: LLM provider to use ('gemini' or 'ollama')
            model: Specific model name to use (optional, uses defaults from .env)
        """
        # This will load environment variables from a .env file if present
        load_dotenv()

        self.provider = provider.lower()
        self.tools = get_file_tools()
        # File where AI responses are appended
        self.response_file = response_file

        # Initialize the appropriate LLM
        if self.provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")

            model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1,
                top_p=0.8,
                top_k=50,
                max_tokens=4096
            )
        elif self.provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://10.0.2.2:11434")
            # keep for error messages
            self.base_url = base_url
            model_name = model or os.getenv("OLLAMA_MODEL", "granite4:micro-h")
            self.llm = ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=0.1,
                top_p=0.8,
                top_k=50,
                max_tokens=8192
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'ollama'")

        env_path = os.getenv("SYSTEM_PROMPT_FILE")
        if env_path:
            system_prompt = load_system_prompt()
        else:
            raise ValueError("SYSTEM_PROMPT_FILE environment variable must be set.")

        tracing.trace_print("Using system prompt:", log_only=True)
        tracing.trace_print(system_prompt, log_only=True)

        self.agent_executor = create_agent(self.llm, self.tools, system_prompt=system_prompt)

    def run(self, query: str) -> str:
        """Run the agent with a user query.

        Args:
            query: The user's query or instruction

        Returns:
            The agent's response
        """
        try:
            result = self.agent_executor.invoke({"messages": [HumanMessage(content=query)]})

            tracing.log_response(result)

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
                    out = normalize_content(last.content)
                elif isinstance(last, dict) and "content" in last:
                    out = normalize_content(last["content"])
                else:
                    out = normalize_content(last)

                # Append to AI_RESPONSE_FILE and return
                try:
                    with open(self.response_file, "a", encoding="utf-8") as f:
                        f.write(out + "\n")
                except Exception as io_err:
                    tracing.trace_print(f"Warning: failed to write {self.response_file}: {io_err}")

                return out

            # Nothing matched; return a readable representation
            out = normalize_content(result)
            try:
                with open(self.response_file, "a", encoding="utf-8") as f:
                    f.write(out + "\n")
            except Exception as io_err:
                tracing.trace_print(f"Warning: failed to write {self.response_file}: {io_err}")
            return out
        except Exception as e:
            msg = str(e)
            out = f"Error executing agent: {msg}"
            tracing.trace_print(out)
            return out

        return "[ERROR] Running agent failed!"

    def chat(self):
        """Start an interactive chat session with the agent."""
        tracing.trace_print(f"Starting chat with {self.provider.upper()} agent...")
        tracing.trace_print("Type 'exit' or 'quit' to end the session.\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    tracing.trace_print("Goodbye!")
                    break

                if not user_input:
                    continue

                response = self.run(user_input)
                tracing.trace_print(f"\nAgent: {response}\n")

            except KeyboardInterrupt:
                tracing.trace_print("\n\nGoodbye!")
                break
            except Exception as e:
                tracing.trace_print(f"\nError: {str(e)}\n")


def main():
    """Main entry point for the agent script."""

    parser = argparse.ArgumentParser(
        description="AI agent with file access tools supporting Gemini and Ollama"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "ollama"],
        required=True,
        help="LLM provider to use (default: gemini)",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Specific model name to use (optional)",
    )
    parser.add_argument(
        "--response-file",
        type=str,
        help="Path to file where AI responses will be appended",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to execute (if not provided, starts interactive mode)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Run the agent in silent tracing mode (log to file only, no console prints)",
    )

    args = parser.parse_args()

    try:
        # Configure tracer silent mode if requested
        tracing.set_silent(args.silent)
        agent = FileAgent(provider=args.provider, model=args.model, response_file=args.response_file)

        if args.query:
            # Single query mode
            response = agent.run(args.query)
            tracing.trace_print(f"\n\nAgent response:\n{response}")
        else:
            # Interactive mode
            agent.chat()

    except Exception as e:
        tracing.trace_print(f"Error initializing agent: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

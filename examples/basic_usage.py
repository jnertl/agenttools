"""Example usage of the FileAgent."""

import os
from agenttools.agent import FileAgent


def example_gemini():
    """Example using Gemini provider."""
    print("=== Example: Using Gemini ===\n")
    
    # Make sure you have GOOGLE_API_KEY set in your .env file
    agent = FileAgent(provider="gemini")
    
    # Example 1: List directory
    print("Query: What files are in the current directory?")
    response = agent.run("What files are in the current directory?")
    print(f"Response: {response}\n")
    
    # Example 2: Read file
    print("Query: Read the README.md file")
    response = agent.run("Read the README.md file and summarize it")
    print(f"Response: {response}\n")


def example_ollama():
    """Example using Ollama provider."""
    print("=== Example: Using Ollama ===\n")
    
    # Make sure Ollama is running locally
    agent = FileAgent(provider="ollama", model="llama2")
    
    # Example: Check if file exists
    print("Query: Check if setup.py exists")
    response = agent.run("Check if setup.py exists and tell me about it")
    print(f"Response: {response}\n")


def example_write_file():
    """Example of writing a file."""
    print("=== Example: Writing a file ===\n")
    
    agent = FileAgent(provider="gemini")
    
    # Create a test file
    print("Query: Create a test file with a greeting")
    response = agent.run(
        "Create a file called /tmp/test_greeting.txt with the content "
        "'Hello from the AI agent! This is a test file.'"
    )
    print(f"Response: {response}\n")
    
    # Verify it was created
    print("Query: Read the test file back")
    response = agent.run("Read the file /tmp/test_greeting.txt")
    print(f"Response: {response}\n")


if __name__ == "__main__":
    print("FileAgent Examples\n")
    print("Note: Make sure you have configured your .env file with appropriate API keys.\n")
    
    # Run examples (comment out the ones you don't want to run)
    
    # Requires GOOGLE_API_KEY
    # example_gemini()
    
    # Requires Ollama running locally
    # example_ollama()
    
    # Simple write/read example
    # example_write_file()
    
    print("\nUncomment the examples in examples/basic_usage.py to run them.")

"""Simple demonstration of the file tools without requiring API keys."""

from agenttools.tools import get_file_tools
import os
import tempfile


def demo_file_tools():
    """Demonstrate the file tools functionality."""
    print("=" * 60)
    print("AgentTools - File Tools Demonstration")
    print("=" * 60)
    print()
    
    # Get all tools
    tools = get_file_tools()
    print(f"Available tools: {', '.join(t.name for t in tools)}")
    print()
    
    # Create a temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_file = os.path.join(temp_dir, "demo.txt")
        
        print("=" * 60)
        print("1. Writing a file")
        print("=" * 60)
        write_tool = [t for t in tools if t.name == "write_file"][0]
        content = """This is a demo file created by agenttools.
It demonstrates the file writing capability.
The agent can create and write to files."""
        result = write_tool.invoke({"file_path": demo_file, "content": content})
        print(f"Result: {result}")
        print()
        
        print("=" * 60)
        print("2. Checking if file exists")
        print("=" * 60)
        exists_tool = [t for t in tools if t.name == "file_exists"][0]
        result = exists_tool.invoke({"file_path": demo_file})
        print(f"Result: {result}")
        print()
        
        print("=" * 60)
        print("3. Reading the file")
        print("=" * 60)
        read_tool = [t for t in tools if t.name == "read_file"][0]
        result = read_tool.invoke({"file_path": demo_file})
        print(f"Content:\n{result}")
        print()
        
        print("=" * 60)
        print("4. Listing directory contents")
        print("=" * 60)
        list_tool = [t for t in tools if t.name == "list_directory"][0]
        result = list_tool.invoke({"directory_path": temp_dir})
        print(result)
        print()
    
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print()
    print("To use the AI agent with these tools:")
    print("1. Set up your .env file with API keys")
    print("2. Run: python -m agenttools.agent --provider gemini")
    print("3. Or: python -m agenttools.agent --provider ollama")


if __name__ == "__main__":
    demo_file_tools()

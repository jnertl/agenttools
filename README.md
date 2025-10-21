# agenttools

A Langchain framework Python project for AI agent scripts with file access tools. This project provides a generic agent that can interact with files and supports both Google Gemini API and Ollama as LLM providers.

## Features

- **File Access Tools**: Read files, write files, list directories, and check file existence
- **Gemini API Support**: Use Google's Gemini models for AI processing
- **Ollama Support**: Use local Ollama models for privacy and offline use
- **Interactive Mode**: Chat with the agent in an interactive session
- **Single Query Mode**: Execute single queries from the command line

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jnertl/agenttools.git
cd agenttools
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Configuration

Create a `.env` file based on `.env.example`:

- **GOOGLE_API_KEY**: Your Google API key for Gemini (required if using Gemini)
- **OLLAMA_BASE_URL**: URL for your Ollama instance (default: http://localhost:11434)
- **LLM_PROVIDER**: Default provider ('gemini' or 'ollama')
- **GEMINI_MODEL**: Gemini model name (default: gemini-pro)
- **OLLAMA_MODEL**: Ollama model name (default: llama2)

## Usage

### Interactive Mode

Start a chat session with the agent:

```bash
# Using Gemini
python -m agenttools.agent --provider gemini

# Using Ollama
python -m agenttools.agent --provider ollama
```

### Single Query Mode

Execute a single query:

```bash
# List files in a directory
python -m agenttools.agent --provider gemini --query "List all files in the current directory"

# Read a file
python -m agenttools.agent --provider ollama --query "Read the contents of README.md"

# Write to a file
python -m agenttools.agent --query "Create a file called test.txt with the content 'Hello, World!'"
```

### Using a Specific Model

```bash
# Use a specific Gemini model
python -m agenttools.agent --provider gemini --model gemini-1.5-pro

# Use a specific Ollama model
python -m agenttools.agent --provider ollama --model llama3
```

## Available Tools

The agent has access to the following file system tools:

1. **read_file**: Read the contents of a file
2. **write_file**: Write content to a file
3. **list_directory**: List files and directories in a path
4. **file_exists**: Check if a file or directory exists

## Requirements

- Python 3.8+
- For Gemini: Google API key
- For Ollama: Local Ollama installation

## Example Queries

- "What files are in this directory?"
- "Read the contents of setup.py"
- "Create a new file called notes.txt with my task list"
- "Check if README.md exists"
- "List all Python files in the agenttools directory"

## Development

Install in development mode:

```bash
pip install -e .
```

## License

MIT License
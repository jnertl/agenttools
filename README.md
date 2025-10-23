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

2. Install Python dependencies:
```bash
uv venv venv_agenttools
. venv_agenttools/bin/activate
uv pip install -r requirements.txt
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
 - **SYSTEM_PROMPT_FILE**: Mandatory path to a text file containing the system prompt. The file may contain placeholders of the form `{{VARNAME}}` which will be replaced by the corresponding environment variable at startup. The agent will fail to start if a referenced environment variable is missing.

## Quick Start

**Try the demo (no API keys needed):**
   ```bash
   python examples/demo_tools.py
   ```

**Run the agent:**
   ```bash
   # With Gemini (requires GOOGLE_API_KEY)
   python -m agenttools.agent --provider gemini
   
   # With Ollama (requires Ollama running locally)
   python -m agenttools.agent --provider ollama
   ```

## Usage

### Demo Without API Keys

To see the file tools in action without needing API keys:

```bash
python examples/demo_tools.py
```

This will demonstrate all four file access tools (read, write, list, exists) working independently.

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
   - If `file_path` contains a directory component (e.g. `logs/app.txt`) the directory will be created if it doesn't exist. If `file_path` is just a filename (e.g. `notes.txt`) the file will be created in the current working directory where the script is invoked.
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

## Architecture

The project is structured around three main components:

### 1. File Tools (`agenttools/tools.py`)
- **read_file**: Read contents from a file
- **write_file**: Write content to a file (creates directories as needed)
- **list_directory**: List files and directories with size information
- **file_exists**: Check if a path exists and get its type

All tools are implemented as Langchain tools using the `@tool` decorator, making them automatically compatible with Langchain agents.

### 2. FileAgent Class (`agenttools/agent.py`)
The `FileAgent` class provides:
- **Multi-provider support**: Works with both Gemini and Ollama
- **Flexible initialization**: Configure provider and model at runtime
- **Two interaction modes**:
  - `run()`: Execute single queries programmatically
  - `chat()`: Interactive command-line interface
- **Error handling**: Graceful handling of API errors and tool failures

### 3. Examples (`examples/`)
- **demo_tools.py**: Demonstrates file tools without requiring API keys
- **basic_usage.py**: Shows how to use the FileAgent programmatically

## License

MIT License

## Possible improvements for robustness

The repository currently supports applying branch changes using the GitHub Contents API (file-level updates) as well as creating pull requests via the REST API. For future hardening and operational robustness consider the following improvements:

- Prefer `git push` for preserving local commit history: reconstructing local commit history via the GitHub API is possible (Git Data API) but more complex and error-prone. If preserving exact commits and metadata is important, keep `git push` as the default for that workflow and offer an API-only mode for headless environments.

- Use the Git Data API for full commit/tree operations if you need to reproduce multiple commits or complex history on the remote. This involves creating blobs, trees and commits and then updating refs.

- Add retries and exponential backoff for transient network/API errors. Wrap API calls with a small retry strategy (3 attempts with jitter) to reduce flakiness.

- Handle large diffs and big files gracefully. The Contents API has size limits; consider uploading very large diffs to a Gist and linking it from the PR body or using Git LFS for large binary files.

- Improve rename detection and handling: currently renames are implemented as delete+add. To preserve rename semantics you would need to detect similarity and call the Git Data API to build a tree with the new path while preserving blob SHAs.

- Add a `--remote` option and explicit `--api-push`/`--git-push` flags so callers can choose the remote update strategy at runtime.

- Add comprehensive unit tests for the API push flow that mock `subprocess` and HTTP (`requests`) interactions to verify expected calls and payloads.

- Add logging and a verbose mode to surface API request/response IDs and errors for easier troubleshooting.

- Validate token scopes and provide clearer error messages when permissions are insufficient (for example: missing `repo` scope for private repos).

These changes will make the PR/branch workflow more reliable across environments (CI, developer machines, and headless containers) and easier to debug when network or API issues occur.

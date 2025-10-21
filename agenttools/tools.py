"""File access tools for AI agents."""

import os
from typing import Optional
from langchain.tools import tool


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        The contents of the file as a string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        A success message or error description
    """
    try:
        # Create directory if it doesn't exist. If `file_path` does not
        # include a directory component (e.g. just 'file.txt'), then write
        # the file into the current working directory where the script was
        # called from.
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_directory(directory_path: str) -> str:
    """List files and directories in a given path.
    
    Args:
        directory_path: Path to the directory to list
        
    Returns:
        A string containing the list of files and directories
    """
    try:
        entries = os.listdir(directory_path)
        if not entries:
            return f"Directory {directory_path} is empty"
        
        files = []
        dirs = []
        for entry in entries:
            full_path = os.path.join(directory_path, entry)
            if os.path.isdir(full_path):
                dirs.append(f"[DIR]  {entry}")
            else:
                size = os.path.getsize(full_path)
                files.append(f"[FILE] {entry} ({size} bytes)")
        
        result = f"Contents of {directory_path}:\n"
        if dirs:
            result += "\nDirectories:\n" + "\n".join(sorted(dirs))
        if files:
            result += "\n\nFiles:\n" + "\n".join(sorted(files))
        
        return result
    except FileNotFoundError:
        return f"Error: Directory not found at {directory_path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def file_exists(file_path: str) -> str:
    """Check if a file or directory exists.
    
    Args:
        file_path: Path to check
        
    Returns:
        A message indicating whether the file/directory exists
    """
    exists = os.path.exists(file_path)
    if exists:
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            return f"File exists at {file_path} ({size} bytes)"
        elif os.path.isdir(file_path):
            return f"Directory exists at {file_path}"
        else:
            return f"Path exists at {file_path} (special file)"
    else:
        return f"Path does not exist: {file_path}"


def get_file_tools():
    """Get a list of all file access tools.
    
    Returns:
        A list of tool functions
    """
    return [read_file, write_file, list_directory, file_exists]

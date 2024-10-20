import argparse
import json
import os
import subprocess
import time
import random
from typing import List, Generator

import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from openai import OpenAIError

# Set up OpenAI API key (ensure this is set in your environment variables)
openai.api_key = os.environ.get("OPENAI_API_KEY")

def list_artifact_files(directory: str) -> List[str]:
    """List all artifact files in the given directory, sorted by their leading number."""
    try:
        files = [f for f in os.listdir(directory)]
        return sorted(files, key=lambda x: int(x.split('_')[0]))
    except Exception as e:
        return [f"Error listing artifact files: {str(e)}"]

def read_file_content(file_path: str) -> str:
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file content: {str(e)}"

def write_file_content(file_path: str, content: str):
    """Write content to a file."""
    try:
        with open(file_path, 'w') as file:
            file.write(content)

        return "File written successfully."
    except Exception as e:
        return f"Error writing file content: {str(e)}"

def list_directory_files(directory: str, max_depth: int = 10) -> str:
    """
    List all files and directories in a tree-like structure.

    Args:
    directory (str): The path to the directory to list.
    max_depth (int): The maximum depth to recurse into subdirectories.

    Returns:
    str: A string representation of the directory structure.
    """
    def tree(dir_path: str, prefix: str = '', depth: int = 0) -> Generator[str, None, None]:
        if depth > max_depth:
            yield prefix + '└── ...'
            return

        contents = list(os.scandir(dir_path))
        pointers = ['├── '] * (len(contents) - 1) + ['└── ']
        for pointer, path in zip(pointers, contents):
            yield prefix + pointer + path.name
            if path.is_dir():
                extension = '│   ' if pointer == '├── ' else '    '
                yield from tree(path.path, prefix + extension, depth + 1)

    return '\n'.join(tree(directory))

tools: List[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Read and return the content of a file in a given path identified by file_path",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_content",
            "description": "Write content to a file on file_path. We'll auto-create the parent directories as required",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    }
]

def exponential_backoff(attempt: int, max_delay: float = 60.0) -> float:
    """Calculate delay with exponential backoff and jitter."""
    delay = min(2 ** attempt + random.uniform(0, 1), max_delay)
    return delay

def retry_openai_request(func, *args, **kwargs):
    """Retry OpenAI request with exponential backoff."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except OpenAIError as e:
            if attempt == max_retries - 1:
                raise
            delay = exponential_backoff(attempt)
            print(f"OpenAI request failed. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)

def process_artifact(artifact_path: str, output_directory: str, model_name: str):
    """Process a single artifact file using the specified model with function calling."""
    artifact_content = read_file_content(artifact_path)

    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": """
            You are an AI agent tasked with analyzing artifact files and creating or updating corresponding output files.

            Use the provided functions to perform file operations as needed. You are responsible for generating or
            updating the files incrementally within a root folder by interpreting the file content to process multiple files.

            Remember the file name is usually given in a comment with the just name and nothing else. Do not interpret the
            filename from anywhere else.
            """},
        {"role": "user", "content": """In an artifact file with the name: '2_Chrome_Plugin_Claude_Artifact_Downloader.js', and content like:

    // manifest.json
    {{
      "manifest_version": 3,
      "name": "Claude Artifact Downloader",
      "version": "1.0",
      "description": "Download artifacts from Claude chat conversations",
      "permissions": ["activeTab", "downloads"],
      "action": {{
        "default_popup": "popup.html"
      }},
      "content_scripts": [
        {{
          "matches": ["https://claude.ai/*"],
          "js": ["content.js"]
        }}
      ]
    }}

    // popup.html
    <!-- Existing content -->
    <body>
      <button id="downloadButton">Download Artifacts</button>
      <script src="popup.js"></script>
    </body>
    </html>

    ---

The inferred files are manifest.json and popup.html with their respective content
that immediately follows the file name. A few things to make sure we're always
extracting the right file contents:
    1. When processing a comment for file name, ALWAYS the comment with the filename
        contains only the file name and nothing else. If you find more content you
        might wanna skip that line. If you can't find a file name, ignore processing.
    2. In the above example for popup.html, we should first read the contents of the
        existing file and attempt to produce a content that effectively merges both of
        them as described.
    3. If the artifact only contains a directory layout structure, do not process that
    file. These type of artifacts usually don't contain any useful stuff."""},
        {"role": "user", "content": f"""
            Analyze this and determine what files need to be created or updated as required.

            Here's the content of an artifact file with the name {os.path.basename(artifact_path)}:

            {artifact_content}"""}
    ]

    while True:
        response = retry_openai_request(
            openai.chat.completions.create,
            model=model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            timeout=30.0,
            temperature=0.2,
            top_p=0.1,
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "read_file_content":
                    if function_args["file_path"] == os.path.basename(artifact_path):
                        file_content = artifact_content
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": file_content})
                    else:
                        full_path = os.path.join(output_directory, function_args["file_path"])
                        print(f"Reading the contents from {full_path}")
                        file_content = read_file_content(full_path)
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": file_content})
                elif function_name == "write_file_content":
                    full_path = os.path.join(output_directory, function_args["file_path"])
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    print(f"Writing / Updating the contents to {full_path}")
                    response_msg = write_file_content(full_path, function_args["content"])
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": response_msg})
        else:
            # If no function is called, assume the task is complete
            print("No tool call in the message, moving on to the next file (if any)")
            break

    print(f"Processed {os.path.basename(artifact_path)}")

def ensure_empty_directory(directory: str):
    """Ensure the output directory is empty, fail if not."""
    if os.path.exists(directory) and os.listdir(directory):
        raise Exception(f"Output directory '{directory}' is not empty. Please provide an empty directory.")

def initialize_git_repo(directory: str):
    """Initialize an empty git repository in the given directory."""
    subprocess.run(["git", "init"], cwd=directory, check=True)
    print(f"Initialized empty Git repository in {directory}")

def create_git_commit(directory: str, artifact_name: str, artifact_content: str):
    """Create a git commit with the given message and description, but only if there are changes."""
    # Check if there are any changes to commit
    result = subprocess.run(["git", "status", "--porcelain"], cwd=directory, capture_output=True, text=True)
    if not result.stdout.strip():
        print(f"No changes to commit for {artifact_name}")
        return

    subprocess.run(["git", "add", "."], cwd=directory, check=True)
    commit_message = f"Processed artifact: {artifact_name}"
    subprocess.run(["git", "commit", "-m", commit_message, "-m", artifact_content], cwd=directory, check=True)
    print(f"Created Git commit for {artifact_name}")

def main():
    parser = argparse.ArgumentParser(description="Process artifact files and generate output files.")
    parser.add_argument("-i", "--input", required=True, help="Input directory containing artifact files")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated files")
    parser.add_argument("-m", "--model", default="gpt-4o-mini", help="OpenAI model to use (default: gpt-4o-mini)")
    parser.add_argument("--ignore-failed", action="store_true", help="Continue processing if a file fails (default: False)")
    args = parser.parse_args()

    artifact_directory = args.input
    output_directory = args.output
    model_name = args.model
    ignore_failed = args.ignore_failed

    # Ensure output directory is empty
    ensure_empty_directory(output_directory)

    os.makedirs(output_directory, exist_ok=True)

    # Initialize empty git repo
    initialize_git_repo(output_directory)

    for artifact_file in list_artifact_files(artifact_directory):
        print(f"Processing {artifact_file}...")
        artifact_path = os.path.join(artifact_directory, artifact_file)

        try:
            process_artifact(artifact_path, output_directory, model_name)

            # Create git commit after processing each artifact
            artifact_content = read_file_content(artifact_path)
            create_git_commit(output_directory, artifact_file, artifact_content)
        except Exception as e:
            print(f"Error processing {artifact_file}: {str(e)}")
            if not ignore_failed:
                print("Stopping processing due to failure.")
                break
            else:
                print("Continuing to next file due to --ignore-failed flag.")

if __name__ == "__main__":
    main()

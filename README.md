# Artifact Processor

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Usage](#usage)
6. [How It Works](#how-it-works)
7. [Configuration](#configuration)
8. [Output](#output)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)

## Introduction

The Artifact Processor is a Python script designed to process artifact files and generate corresponding output files. It uses OpenAI's language models to analyze the content of artifact files and create or update files based on the analysis. This tool is particularly useful for automating the generation of code, configuration files, or other text-based assets from high-level descriptions or specifications.

>> This project was primarily intended to work with ZIP files downloaded using https://github.com/ashwanthkumar/claude-artifacts-downloader

## Features

- Process multiple artifact files in a directory
- Use OpenAI's language models for content analysis and generation
- Configurable OpenAI model selection
- Automatic Git repository initialization and commit creation
- Empty output directory verification
- Error handling and logging

## Requirements

- Python 3.6+
- OpenAI Python library
- Git (for repository initialization and commits)

## Installation

1. Clone this repository or download the script.

2. Install the required Python packages:

   ```
   pip install openai
   ```

3. Set up your OpenAI API key as an environment variable:

   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Usage

Run the script from the command line with the following syntax:

```
python main.py -i <input_directory> -o <output_directory> [-m <model_name>]
```

Arguments:
- `-i` or `--input`: Path to the input directory containing artifact files (required)
- `-o` or `--output`: Path to the output directory for generated files (required)
- `-m` or `--model`: OpenAI model to use (optional, default: "gpt-4o-mini")

Example:
```
python main.py -i ./artifacts -o ./output -m gpt-4-turbo-preview
```

## How It Works

1. The script first checks if the output directory is empty. If not, it fails with an error message.
2. It initializes an empty Git repository in the output directory.
3. For each artifact file in the input directory:
   a. The file content is read and sent to the specified OpenAI model for analysis.
   b. Based on the model's response, the script creates or updates files in the output directory.
   c. After processing each artifact, a Git commit is created with the artifact file name as the commit message and its content as the commit description.
4. The script uses function calling to perform file operations, allowing the AI model to read and write files as needed.

## Configuration

The main configurable aspect of the script is the OpenAI model used for processing. You can specify different models using the `-m` or `--model` argument. Some options include:

- gpt-4o-mini (default)
- gpt-4o

Refer to OpenAI's documentation for the most up-to-date list of available models.

## Output

The script generates files in the specified output directory based on the content of the artifact files. The structure and content of the output files depend on the instructions contained within the artifact files and the AI model's interpretation of those instructions.

Additionally, the script initializes a Git repository in the output directory and creates a commit for each processed artifact, allowing you to track changes and the progression of file generation.

## Troubleshooting

Common issues and their solutions:

1. **OpenAI API key not found**: Ensure that you've set the `OPENAI_API_KEY` environment variable with your valid API key.

2. **Git not installed**: Make sure Git is installed on your system and accessible from the command line.

3. **Permission denied**: Ensure you have write permissions for the output directory.

4. **Model not found**: If you receive an error about the model not being found, check that you've specified a valid OpenAI model name.

## Contributing

Contributions to improve the Artifact Processor are welcome! Please follow these steps to contribute:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes and commit them with clear, descriptive messages
4. Push your changes to your fork
5. Submit a pull request with a clear description of your changes

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

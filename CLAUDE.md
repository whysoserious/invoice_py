# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run script: `python process_invoices.py --folder <folder_path> --api-key <anthropic_api_key>`
- Environment setup: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Compile check: `python3 -m py_compile process_invoices.py && echo "Compilation successful - no syntax errors"`
- Format code: `black *.py`
- Lint code: `flake8 *.py`
- Cleanup: `find test_kantor/ -type f \( -name "*.jpg" -o -name "*.csv" \) -delete`

## Code Style Guidelines
- Use PEP 8 style guidelines for Python code
- Imports order: standard library, third-party, local
- Use type hints for function parameters and return values
- Use descriptive variable names in English
- Handle exceptions with specific exception types
- All comments, log messages, and error messages should be in English
- Maintain 4-space indentation
- Line length max: 100 characters
- Use docstrings for functions and classes
- Maintain consistent error handling approach using try/except blocks
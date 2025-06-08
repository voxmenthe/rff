#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status

echo "Setting up Python project with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi


# Initialize the project (if not already initialized)
if [ ! -f "pyproject.toml" ]; then
    echo "Initializing new uv project..."
    uv init --name scraping .
else
    echo "Project already initialized, skipping uv init"
fi

# Sync dependencies and create virtual environment
echo "Syncing dependencies and creating virtual environment..."
uv sync

# Create and install the IPython kernel for the project
echo "Installing Jupyter kernel..."
uv run python -m ipykernel install --user --name=cot-scaffold --display-name "CoT Scaffold"

echo "Jupyter kernel 'cot-scaffold' has been installed."

# Create a directory for package versions
mkdir -p package_versions

# Freeze the package versions and save to a file
file_path="package_versions/pv_$(date +%Y%m%d).txt"

echo "Python Version: $(uv run python --version 2>&1)" > "$file_path"

echo -e "\n--- UV Lock Output ---" >> "$file_path"
if [ -f "uv.lock" ]; then
    echo "Lock file exists, dependencies managed by uv.lock" >> "$file_path"
else
    echo "No lock file found" >> "$file_path"
fi

echo -e "\n--- Installed Packages ---" >> "$file_path"
uv run pip list >> "$file_path"

echo "Project setup complete!"
echo "Virtual environment created at: .venv"
echo "To activate: source .venv/bin/activate (or use 'uv run' for commands)"
echo "Setup complete! You can now:"
echo "  - Run scripts with: uv run <script.py>"
echo "  - Add dependencies with: uv add <package>"
echo "  - Install dev dependencies with: uv sync --group dev"
echo "  - Activate environment with: source .venv/bin/activate"


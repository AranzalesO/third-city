#!/bin/bash
# Helper script to run the Brand Monitoring Tool with correct Python environment
# For Git Bash / WSL / Linux / macOS

echo ""
echo "================================================================================"
echo " Brand Monitoring Tool - Launcher (Bash)"
echo "================================================================================"
echo ""
echo "Activating virtual environment..."
source venv/Scripts/activate

echo ""
echo "Running analysis..."
python -m src.main

echo ""
echo "================================================================================"
echo " Analysis Complete"
echo "================================================================================"
echo ""

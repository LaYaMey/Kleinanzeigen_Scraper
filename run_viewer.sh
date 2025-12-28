#!/bin/bash

# --- 1. ENVIRONMENT SETUP ---
# Source Conda's initialization script
source ~/anaconda3/etc/profile.d/conda.sh

# Activate the environment
conda activate ebay_pipeline

# --- 2. DIRECTORY SETUP ---
# Switch to the directory where this script is located
cd "$(dirname "$0")/Scrapy_Project" || { echo "Error: Project folder not found!"; exit 1; }

# --- 3. RUN STREAMLIT ---
echo "Starting Dataset Viewer..."
echo "Press Ctrl+C to stop the server."
echo "--------------------------------"

# Run the app located in the subfolder
streamlit run dataset_viewer/dataset_viewer.py
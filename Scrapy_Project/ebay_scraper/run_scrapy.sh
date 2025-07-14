#!/bin/bash

# Source Conda's initialization script
source ~/anaconda3/etc/profile.d/conda.sh  # Adjust path if Conda is installed elsewhere

# Activate the environment
conda activate ebay_pipeline

# Run Scrapy
scrapy crawl laptops_kleinanzeigen


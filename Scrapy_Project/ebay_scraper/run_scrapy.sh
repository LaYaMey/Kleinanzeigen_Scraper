#!/bin/bash

# --- 1. ENVIRONMENT SETUP ---
# Source Conda's initialization script (Adjust path if necessary)
source ~/anaconda3/etc/profile.d/conda.sh

# Activate the environment
conda activate ebay_pipeline

# --- 2. DIRECTORY SETUP ---
# Switch to the directory where this script is located.
# This ensures Scrapy finds the 'scrapy.cfg' and 'jobs/' folder correctly.
cd "$(dirname "$0")"

# --- 3. DEFINE JOB LIST ---
# Add the filenames of the JSON files you created in the 'jobs' folder here.
# You can add as many as you like.
JOBS=(
    "job_mums_17inch.json"
    "job_gaming_laptop.json"
    # "job_garden_tools.json"
)

# --- 4. EXECUTION LOOP ---
echo "=========================================="
echo "Starting Scraper Batch Run"
echo "=========================================="

for job_file in "${JOBS[@]}"
do
    full_path="jobs/$job_file"

    if [ -f "$full_path" ]; then
        echo ">>> Running Job: $job_file"
        
        # Run the spider with the specific config
        scrapy crawl kleinanzeigen_scraper -a job_config="$full_path"
        
        echo ">>> Finished: $job_file"
        echo "------------------------------------------"
        
        # OPTIONAL: Sleep for 5 seconds between jobs to be polite to the server
        # and reduce the risk of IP bans.
        sleep 5
    else
        echo "!!! ERROR: Config file not found: $full_path"
        echo "------------------------------------------"
    fi
done

echo "Batch Run Complete."
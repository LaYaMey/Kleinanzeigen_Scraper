# Kleinanzeigen Scraper & Dataset Viewer

This project provides a modular **Scrapy** pipeline to scrape listings from *Kleinanzeigen.de* based on configurable job files, along with a **Streamlit** dashboard to visualize, filter, and extract hardware specifications (RAM, SSD, CPU) from the data.

## 📂 Project Structure

```text
├── run_scrapy.sh               # Entry point to run the scraper batch
├── run_viewer.sh               # Entry point to launch the Streamlit viewer
├── requirements.txt            # Python dependencies
├── Scrapy_Project/
│   ├── jobs/                   # Configuration files (JSON) for scrape tasks
│   ├── data/                   # Storage for scraped JSON datasets
│   ├── dataset_viewer/         # Streamlit app and Heuristic Feature Extractor
│   └── ebay_scraper/           # Core Scrapy spiders and settings
```

## 🚀 Setup

1.  **Create Environment:**
    It is recommended to use **Python 3.12** to ensure binary compatibility with Pandas and Scrapy (avoiding compilation errors often found with newer Python versions).
    ```bash
    conda create -n ebay_pipeline python=3.12 -y
    conda activate ebay_pipeline
    ```
    If you use a different environment 

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

> **⚠️ Note on Shell Scripts:**
> The provided scripts (`run_scrapy.sh` and `run_viewer.sh`) are pre-configured to look for a Conda environment named **`ebay_pipeline`**.
>
> If you are using a different environment name, or a different package manager (like `venv`, `poetry`, etc.), **please open and edit these `.sh` files** to match your specific activation command.

## 🛠 Usage

### 1. Run the Scraper
To start scraping the defined jobs:
```bash
./run_scrapy.sh
```
*   This processes the job list defined inside the script.
*   Results are saved to `Scrapy_Project/data/`.

### 2. Run the Viewer
To explore the data with heuristic filters (RAM, CPU Gen, SSD size):
```bash
./run_viewer.sh
```
*   Opens a web interface at `http://localhost:8501`.

## ⚙️ Adding New Scrape Jobs

1.  **Create a Job Config:**
    Add a new `.json` file in `Scrapy_Project/jobs/` (e.g., `job_macbook.json`):
    ```json
    {
        "task_name": "Macbook Search",
        "output_filename": "data_macbooks.json",
        "scrape_next_pages": true,
        "start_urls": [
            "https://www.kleinanzeigen.de/s-macbook-m1/k0"
        ]
    }
    ```

2.  **Register the Job:**
    Open `run_scrapy.sh` and add the filename to the `JOBS` array:
    ```bash
    JOBS=(
        "job_mums_17inch.json"
        "job_gaming_laptop.json"
        "job_macbook.json"      # <--- Added new job
    )
    ```

## 💾 Data Directory
Scraped data is stored in **`Scrapy_Project/data/`**.
*   The scraper automatically creates output files here (e.g., `data_gaming_laptops.json`).
*   The Viewer looks specifically in this folder to load datasets.

---
*Note: This README was created with the assistance of Gemini 3 Pro Preview.*
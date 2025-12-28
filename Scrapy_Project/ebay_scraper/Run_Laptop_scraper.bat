REM Set the desired directory path
set WORKING_DIRECTORY=D:\Documents\Programmieren\Python\Kleinanzeigen_Scraper\Scrapy_Project\ebay_scraper

REM Change the current directory
cd /d %WORKING_DIRECTORY%

REM === RUN JOB 1: MUMS LAPTOPS ===
scrapy crawl kleinanzeigen_scraper -a job_config="jobs/job_mums_17inch.json"

REM === RUN JOB 2: GAMING LAPTOPS (Optional, just uncomment to run) ===
REM scrapy crawl kleinanzeigen_scraper -a job_config="jobs/job_gaming.json"

pause
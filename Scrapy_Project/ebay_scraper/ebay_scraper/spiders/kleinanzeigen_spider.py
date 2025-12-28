from pathlib import Path
import re
import os
import scrapy


#from Scrapy_Project\ebay_scraper\ebay_scraper\spiders\utilities import Utilities
#from utilities import Utilities
from ebay_scraper.spiders.utilities import Utilities


class KleinanzeigenSpider(scrapy.Spider):
    name = "kleinanzeigen_scraper"
    
    def __init__(self, job_config=None, *args, **kwargs):
        super(KleinanzeigenSpider, self).__init__(*args, **kwargs)
        
        self.utilities = Utilities()
        self.utilities.log_scraper_run("run_log.txt")

        if job_config:
            # Load the specific JSON file passed from the command line
            self.config = self.utilities.load_config_file(job_config)
            self.start_urls = self.config['start_urls']
            self.logger.info(f"Loaded Job: {self.config['task_name']}")

            raw_filename = self.config.get("output_filename", "fallback.json")
            self.config["output_filename"] = os.path.join("data", raw_filename)


        else:
            # Fallback or Error if no file is provided
            self.logger.error("No job_config file provided! Use -a job_config=path/to/file.json")
            self.start_urls = []
            self.config = {}


    def parse(self, response, **kwargs):
        scrape_next_page = self.config.get("scrape_next_pages", False)

        # 1. Container finden
        ad_articles = response.xpath("//article[contains(@class, 'aditem')]")
        self.logger.info(f"Page Analysis: Found {len(ad_articles)} ad containers on {response.url}")

        existing_data = self.utilities.open_json(self.config.get("output_filename", "fallback_data.json"))

        for index, ad in enumerate(ad_articles):
            # URL holen
            url_relative = ad.xpath(".//a[contains(@class, 'ellipsis')]/@href").get()
            
            if not url_relative:
                # Manchmal ist der Link direkt auf dem Artikel oder anders verschachtelt
                # Fallback Versuche
                url_relative = ad.xpath(".//a[contains(@href, '/s-anzeige/')]/@href").get()
                if not url_relative:
                    self.logger.warning(f"Ad {index}: No URL found. Skipping.")
                    continue

            # TopAd Check
            is_top_ad = ad.xpath("./ancestor::li[contains(@class, 'is-topad')]")
            if is_top_ad:
                self.logger.info(f"Ad {index}: Skipped (TopAd/Werbung)")
                continue

            # ID Check - NUR AUS URL (für langes Format)
            # URL Format ist: /s-anzeige/titel-bla-bla/123456789-123-456
            # Split by '/' first, take the last part, then split by '?' to remove tracking codes
            doc_id = url_relative.split("/")[-1].split("?")[0]

            if existing_data:
                if any(entry.get("ID") == doc_id for entry in existing_data):
                    self.logger.info(f"Ad {index}: Skipped (Duplicate ID {doc_id})")
                    if scrape_next_page:
                        scrape_next_page = False
                    continue
            
            # Request erstellen
            article_page = response.urljoin(url_relative)
            yield scrapy.Request(
                url=article_page, 
                callback=self.parse_article_page, 
                dont_filter=True,
                meta={'doc_id': doc_id} # LANGE ID weiterreichen
            )

        # Pagination
        next_page_relative = response.xpath("//a[@class='pagination-next']/@href").get()
        if next_page_relative and scrape_next_page:
            next_page_url = response.urljoin(next_page_relative)
            self.logger.info(f"Pagination: Navigating to next page: {next_page_url}")
            yield scrapy.Request(next_page_url, callback=self.parse)

    def parse_article_page(self, response):
        doc_id = response.meta.get('doc_id', 'Unknown')
        article_url = response.url

        # Titel extrahieren
        article_title = response.xpath("//h1[@id='viewad-title']/text()").get()
        if not article_title:
            article_title = response.xpath("//h1[@class='boxedarticle--title']//text()").get()
        
        if not article_title:
            self.logger.error(f"FAILED to parse Title for ID {doc_id} ({article_url}). Layout changed or blocked?")
            return 

        article_title = article_title.strip()

        # Preis
        article_price = response.xpath("//h2[@id='viewad-price']/text()").get()
        if not article_price:
            article_price = response.xpath("//h2[@class='boxedarticle--price']//text()").get()

        if article_price:
            # FIX: r"..." für Raw String, um die SyntaxWarning zu beheben
            article_price = re.sub(r"[€VB\s]", "", article_price).strip().replace(".", "")
        else:
            article_price = "0"

        # Beschreibung
        desc_lines = response.xpath("//div[@id='viewad-description-text']//text()").extract()
        if not desc_lines:
            desc_lines = response.xpath("//p[@itemprop='description']//text()").extract()
        article_description = " ".join([line.strip() for line in desc_lines if line.strip()])

        # Ort & Datum
        locality = response.xpath('//span[@id="viewad-locality"]/text()').get()
        if locality:
            locality = locality.strip()
        else:
            loc_raw = response.xpath('//div[@itemprop="address"]/span[@itemprop="locality"]/text()').get()
            locality = loc_raw.strip() if loc_raw else "Unknown"

        date = response.xpath('//div[@id="viewad-extra-info"]/div/span/text()').get()
        if date: 
            date = date.strip()

        # Seller ID
        try:
            seller_link = response.xpath("//a[contains(@href, 'userId=')]/@href").get()
            if seller_link:
                seller_id = seller_link.split("userId=")[-1].split("&")[0]
            else:
                seller_id = "0"
        except Exception:
            seller_id = "0"

        article = {
            "ID": doc_id,
            "URL": article_url,
            "Preis": article_price,
            "Seller_ID": seller_id,
            "Artikelstitel": article_title,
            "Artikelsbeschreibung": article_description,
            "Date": date,
            "Place": locality
        }

        # Daten verarbeiten
        article = self.utilities.infer_data_types(article)
        
        # Speichern
        self.utilities.add_listing_to_json(article, self.config.get("output_filename", "fallback_data.json"))
        
        # Erfolgsnachricht (Scrapy zählt das Item jetzt)
        yield article
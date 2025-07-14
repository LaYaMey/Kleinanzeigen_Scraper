from pathlib import Path
import re

import scrapy


#from Scrapy_Project\ebay_scraper\ebay_scraper\spiders\utilities import Utilities
#from utilities import Utilities
from ebay_scraper.spiders.utilities import Utilities


class KleinanzeigenSpider(scrapy.Spider):
    name = "laptops_kleinanzeigen"
    
    def __init__(self):
        
        self.utilities = Utilities()
        self.start_urls = self.utilities.load_urls("start_urls.json")
        self.config = self.utilities.load_config_file("config_file.json")

        self.utilities.log_scraper_run("run_log.txt")

    # def start_requests(self): #default implementation of start_requests will automatically triggered with class parameter start_urls[] 
    #     urls = [
    #         "https://quotes.toscrape.com/page/1/",
    #         "https://quotes.toscrape.com/page/2/",
    #     ]
    #     for url in urls:
    #         yield scrapy.Request(url=url, callback=self.parse)

    # def parse(self, response): #parse() is default callback function for Requests
    #     listing_page_links = response.css("li.ad-listitem a").attrib["href"]
    #     yield from response.follow_all(listing_page_links, self.parse_listing)

    #     pagination_links = response.css("li.next a")
    #     yield from response.follow_all(pagination_links, self.parse)

    # def parse_listing(self, response):
    #     pass

    def parse(self, response):
        scrapte_next_page = self.config["scrape_next_pages"] == "True"

        article_urls = response.xpath("//a[@class='ellipsis']/@href").extract()
        li_class_names_list = response.xpath("//ul[@id='srchrslt-adtable']//li[contains(@class, 'ad-listitem  ')]/@class").extract()
        #print(len(li_class_names_list))
        #for i in range(len(li_class_names_list)):
        #    print(f"{i:03}: {li_class_names_list[i]} | {article_urls[i]}")
        domain = 'https://www.kleinanzeigen.de'
        
        existing_data = self.utilities.open_json(self.config["putput_path"])

        for url, class_name, i in zip(article_urls, li_class_names_list, range(len(li_class_names_list))):

            # Check if the listing is topped by looking for the "badge-topad" class
            if "is-topad" in class_name:
                self.logger.debug(f"{i:03}: Skipped Top Ad")
                continue

            doc_id = url.split("/")[-1] #Get the article's ID available in the URL
            if existing_data:
                if any(entry.get("ID") == doc_id for entry in existing_data):
                    self.logger.debug(f"{i:03}: Listing ID {doc_id} already in JSON file. Stopping parsing of further pages.")
                    if scrapte_next_page:
                        scrapte_next_page = False
                    continue
            
            article_page = response.urljoin(domain + url)
            self.logger.debug(f"{i:03}: ===Scraping=== : {url}")
            request = scrapy.Request(url = article_page, callback=self.parse_article_page, dont_filter=True)
            yield request

        next_page = domain + str(response.xpath("//a[@class='pagination-next']/@href").extract_first())
        
        if next_page is not None and scrapte_next_page: #If still some next pages to follow and if it's agreed in the config
            #print(next_page)
            yield scrapy.Request(
            response.urljoin(next_page),
            callback=self.parse)

    def parse_article_page(self, response):

        #Retrieve some data about the article
        article_url = response.url
        article_title = response.xpath("//h1[@class='boxedarticle--title']//text()").extract_first().strip()
        article_price = response.xpath("//h2[@class='boxedarticle--price']//text()").extract_first()
        article_price = re.sub("[€VB]","",article_price).strip().replace(".","")
        if article_price == "":
            return
        article_description = response.xpath("//p[@itemprop='description']").extract_first().split("\n")[-1].strip()
        doc_id = article_url.split("/")[-1] #Get the article's ID available in the URL
        date = response.xpath('//div[@id="viewad-extra-info"]/div[1]/span/text()').get()
        locality = response.xpath('//div[@itemprop="address"]/span[@itemprop="locality"]/text()').get().strip()
        try:
            seller_id = response.xpath("//a[@class='badge user-profile-vip-badge']/@href").extract_first().split("=")[-1]
        except AttributeError:
            #Professional Users will throw this. Hopefully they will not reenter same items, therefore just ignoring and setting to 0
            seller_id="0"

        #Create dictionary from data
        article = []
        article.append(("ID", doc_id))
        article.append(("URL", article_url))
        article.append(("Preis", article_price))
        article.append(("Seller_ID", seller_id))
        article.append(("Artikelstitel", article_title))
        article.append(("Artikelsbeschreibung", article_description))
        article.append(("Date", date))
        article.append(("Place", locality))
        article = dict(article) #Transformation into a dictionary

        
        
        
        #Transform possible values into float or dates
        article = self.utilities.infer_data_types(article)


        #print(article)
        #Write article to json
        self.utilities.add_listing_to_json(article, self.config["putput_path"])

        yield article
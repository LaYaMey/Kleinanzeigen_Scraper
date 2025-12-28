import scrapy
import re
import os
import json
from datetime import datetime
import logging
import time

class Utilities:

    def load_config_file(self, filename="config_file.json"):
        with open(filename, 'r', encoding='utf-8') as file:
            config = json.load(file)
            return config

    def is_int(self, value):
        try:
            int(str(value))
            return True
        except ValueError:
            return False

    def is_float(self, value):
        try:
            float(str(value))
            return True
        except ValueError:
            return False

    def is_date(self, value):
        try:
            datetime.strptime(str(value), '%d.%m.%Y')
            return True
        except ValueError:
            return False

    def infer_data_types(self, article):
        for key in article:
            if isinstance(article[key], list): continue 
            elif self.is_int(article[key]): article[key] = int(article[key])
            elif self.is_float(article[key]): article[key] = float(article[key])
            #elif self.is_date(article[key]) and str(article[key]) is not None: article[key] = datetime.strptime(str(article[key]), '%d.%m.%Y')
        return article
    
    def open_json(self, existing_filename):
        try:
            with open(existing_filename, 'r', encoding='utf-8') as json_file:
                existing_data = json.load(json_file)
            return existing_data
        except FileNotFoundError:
            print(f'The file {existing_filename} does not exist.')
            return
        except json.decoder.JSONDecodeError:
            print(f'The file {existing_filename} exists but is not a valid JSON file.')
            return
        
    def is_listing_id_in_json(self, doc_id, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as json_file:
                existing_data = json.load(json_file)
                # Assuming the JSON structure is a list of dictionaries, each representing a listing
                return any(entry.get("ID") == doc_id for entry in existing_data)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            # Either the file doesn't exist or it's not a valid JSON file, consider the ID not present
            return False


    def add_listing_to_json(self, new_listing, existing_filename):
        # Check if the file exists
        if not os.path.exists(existing_filename):
            print(f'The file {existing_filename} does not exist. Creating a new file.')
            with open(existing_filename, 'w', encoding='utf-8') as json_file:
                json.dump([new_listing], json_file, ensure_ascii=False, indent=4)
            print(f'Listing with ID {new_listing["ID"]} added to {existing_filename}')
            return

        # Load existing data from the JSON file
        try:
            with open(existing_filename, 'r', encoding='utf-8') as json_file:
                existing_data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            print(f'The file {existing_filename} exists but is not a valid JSON file. Creating a new file.')
            with open(existing_filename, 'w', encoding='utf-8') as json_file:
                json.dump([new_listing], json_file, ensure_ascii=False, indent=4)
            print(f'Listing with ID {new_listing["ID"]} added to {existing_filename}')
            return

        # Check if the listing with the given ID already exists
        existing_ids = set(entry.get('ID') for entry in existing_data)
        new_listing_id = new_listing.get('ID')

        if new_listing_id not in existing_ids:
            # Append the new listing to the existing data
            existing_data.append(new_listing)

            # Save the updated dataset back to the JSON file
            with open(existing_filename, 'w', encoding='utf-8') as json_file:
                json.dump(existing_data, json_file, ensure_ascii=False, indent=4)

            print(f'Listing with ID {new_listing_id} added to {existing_filename}')
        else:
            print(f'Listing with ID {new_listing_id} already exists in {existing_filename}. Skipped when writing.')



    def log_scraper_run(self, logfile_path):
        # Check if the logfile exists, and create it if missing
        if not os.path.exists(logfile_path):
            #print(f"Creating log file: {logfile_path}")
            with open(logfile_path, 'w') as log_file:
                pass  # Create an empty file

        # Get the current date and time
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Append a line to the logfile
        with open(logfile_path, 'a') as log_file:
            log_file.write(f"Scraper ran {current_datetime}\n")


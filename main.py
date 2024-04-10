import os
import logging
import logging_config
from multiprocessing import Pool
from scraper_manager import OlxScraper
from database_manager import DatabaseManager
from notification_manager import Messenger
from utils import BASE_DIR
import time
from datetime import datetime
import pytz

scraper = OlxScraper()
db = DatabaseManager()


def load_target_urls() -> list:
    """
    Fetch the list of URLs to monitor from the file 'target_urls.txt',
    which is located in the same directory as the script.

    Returns:
        list: list of URLs from which to collect data. If the
        file does not exist, it creates it and returns an empty list.

    """
    file_path = os.path.join(BASE_DIR, "target_urls.txt")
    user_message = f"The file 'target_urls.txt' has been created. Add " \
                   + f"in it at least one URL to monitor for new ads. Add 1 URL per line."
    try:
        with open(file_path) as f:
            target_urls = [line.strip() for line in f]
    except FileNotFoundError:
        logging.info(user_message)
        open(file_path, "w").close()
        target_urls = []
    if not target_urls:
        logging.info(user_message)
    return target_urls


def get_new_ads_urls(all_ids: list, target_url: str) -> list:
    """
    Returns a list of new ad URLs (not found in the database). 

    Args:
        all_urls (list): list of URLs to be matched against the database.

    Returns:
        new_urls (list): List of URLs not found in the database.
    """
    new_urls, new_ids = get_new_ads_urls_for_url(target_url)

    new_urls_list = []
    new_id_list = []

    if new_urls:
        for id, url in zip(new_ids, new_urls):
            if not id in all_ids:
                new_urls_list.append(url)
                new_id_list.append(id)

    return new_urls_list, new_id_list


def get_new_ads_urls_for_url(target_url: str) -> list:
    """
    Extracts ads for a specific URL and filters out previously processed ads.

    Args:
        target_url (str): A string representing the URL for which new ads should be retrieved.

    Returns:
        List[str]: A list of URLs representing new ads retrieved from the monitored URL.
    """

    try:
        ads_urls, new_ids = scraper.scrape_ads_urls(target_url)
    except ValueError as error:
        logging.error(error)
        return []
    return list(ads_urls), new_ids


def main() -> None:
    """
    Main function. Collects and processes ads
    and sends notifications by email and Telegram.
    """

    target_urls = load_target_urls()
    # добавити масив при добвавленні нової силки
    old_id_masive = [[], [], [], [], []]

    kiev_timezone = pytz.timezone('Europe/Kiev')

    time_reset_1 = True
    time_reset_2 = True
    time_reset_3 = True

    while True:
        # print(old_id_masive)
        # print(target_urls)
        index = 0

        # Отримуємо поточний час за київським часом
        current_time = datetime.now(kiev_timezone)

        if current_time.hour == 8 and time_reset_1:
            time_reset_1 = False
            time_reset_2 = True

            old_id_masive = [[], [], [], [], []]

        # Перевіряємо, чи поточний час дорівнює 17:00 або 8:00
        if current_time.hour == 17 and time_reset_2:
            time_reset_2 = False
            time_reset_1 = True
            time_reset_3 = True
            old_id_masive = [[], [], [], [], []]

        if current_time.hour == 0 and time_reset_3:
            time_reset_3 = False
            time.sleep(1800)

        if current_time.hour >= 2 and current_time.hour <= 7:
            continue

        for target_url, ads_ids in zip(target_urls, old_id_masive):
            # ads_urls = get_new_ads_urls_for_url(target_url)
            # print(ads_ids)

            try:
                # Filter out the already processed ads
                new_ads_urls, new_ids = get_new_ads_urls(ads_ids, target_url)
                # print(new_ads_urls)
            except Exception as e:
                # Messenger.send_telegram_message('', 'Failed')
                continue

            print(f"old {index} {ads_ids}")
            print(f"new {index} {new_ads_urls}")
            # print(f"new {index} {new_ids}")

            # Process ads in parallel, for increased speed
            # with Pool(10) as pool:
            #     new_ads = pool.map(scraper.get_ad_data, new_ads_urls)
            # new_ads = list(filter(None, new_ads))

            if new_ads_urls:
                for ad in new_ads_urls:
                    message_subject, message_body = Messenger.generate_email_content(
                        target_url, [ad])
                    #     Messenger.send_email_message(message_subject, message_body)
                    Messenger.send_telegram_message('', message_body)

            # Add the processed ads to database

            old_id_masive[index].extend(new_ids)
            index = index + 1
            # time.sleep(10)

if __name__ == "__main__":
    main()

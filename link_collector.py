#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Link Collector for Poskok Scraper
--------------------------------
Collects article links from poskok.info by category, archive, and homepage.
Saves them to a JSON file for later processing.
"""

from bs4 import BeautifulSoup
import requests
import re
import os
import time
import random
import json
import logging
from datetime import datetime
from pathlib import Path

# At the top after the imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_detailed.log"),
        logging.StreamHandler()
    ]
)

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import constants from config file
from config import (
    CATEGORY_MAP, BLACKLISTED_URLS, BLACKLISTED_TERMS,
    ITALIAN_INDICATORS, ENGLISH_INDICATORS, USER_AGENTS
)

def get_random_headers():
    """Returns random headers with different User-Agent values."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

def is_blacklisted(url, title=None):
    """Checks if URL or title is blacklisted."""
    # 1. Direct URL check
    if url in BLACKLISTED_URLS:
        logger.info(f"URL on blacklist: {url}")
        return True

    # 2. Title check (if available)
    if title:
        title_lower = title.lower()

        # Quick check for English articles - if title starts with English words
        english_starters = ['the ', 'a ', 'an ', 'this ', 'that ', 'these ', 'those ', 'helicopter', 'james', 'trump']
        if any(title_lower.startswith(starter) for starter in english_starters):
            logger.info(f"Title starts with typical English words: {title}")
            return True

        # Check if there are enough English words in the title
        english_word_count = sum(1 for word in ENGLISH_INDICATORS if word in title_lower)
        if english_word_count >= 3:
            logger.info(f"Title contains too many English words ({english_word_count}): {title}")
            return True

        # Check for blacklisted terms
        for term in BLACKLISTED_TERMS:
            if term in title_lower:
                logger.info(f"Title contains blacklisted term '{term}': {title}")
                return True

    # 3. Check URL path for blacklisted terms
    for term in BLACKLISTED_TERMS:
        if term.replace(" ", "-") in url.lower():
            logger.info(f"URL contains blacklisted term '{term}': {url}")
            return True

    # 4. Check for language indicators in URL path
    language_indicators = ['/en/', '/eng/', '/english/', '/it/', '/ita/', '/italian/']
    for indicator in language_indicators:
        if indicator in url.lower():
            logger.info(f"URL contains language indicator '{indicator}': {url}")
            return True

    return False

def get_page_content(url, max_retries=5, retry_delay=5, timeout=45):
    """Gets page content with retry mechanism."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=timeout)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:
                logger.warning(f"Page does not exist (404): {url}")
                return None
            elif response.status_code == 403:
                logger.warning(f"Access forbidden (403): {url}")
                time.sleep(retry_delay * 2)
            else:
                logger.warning(f"Attempt {attempt+1}/{max_retries}: Status code {response.status_code} for {url}")
                time.sleep(retry_delay)
        except requests.exceptions.Timeout:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Timeout for {url}")
            time.sleep(retry_delay)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Connection problem for {url}")
            time.sleep(retry_delay * 2)
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Error {str(e)} for {url}")
            time.sleep(retry_delay)

    logger.error(f"Failed to retrieve after {max_retries} attempts: {url}")
    return None

def get_homepage_links(base_url):
    """Gets article links from the homepage."""
    logger.info(f"Getting articles from homepage: {base_url}")
    content = get_page_content(base_url)
    if not content:
        return []

    soup = BeautifulSoup(content, 'html.parser')
    links = set()

    # Find all articles on the homepage
    article_elements = soup.find_all(['article', 'div'], class_=lambda c: c and ('item' in str(c).lower() or 'td-module' in str(c).lower()))

    for article in article_elements:
        # Find links in headings (h1, h2, h3, h4)
        heading_tags = article.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in heading_tags:
            link = heading.find('a')
            if link and 'href' in link.attrs:
                href = link['href']
                title = link.get_text(strip=True)

                if 'poskok.info' in href and '/category/' not in href and '/tag/' not in href:
                    # Check blacklist
                    if not is_blacklisted(href, title):
                        links.add(href)

        # Find links directly in the article
        article_links = article.find_all('a', href=True)
        for link in article_links:
            href = link['href']
            title = link.get_text(strip=True)

            if 'poskok.info' in href and '/category/' not in href and '/tag/' not in href:
                # Check if the link leads to an article (not to a category, tag, etc.)
                if any(segment in href for segment in ['2023/', '2024/', '2022/', '.html']):
                    # Check blacklist
                    if not is_blacklisted(href, title):
                        links.add(href)

    logger.info(f"Found {len(links)} links on homepage")
    return list(links)

def get_article_links(category_url):
    """Gets article links from a category page."""
    content = get_page_content(category_url)
    if not content:
        return []

    soup = BeautifulSoup(content, 'html.parser')
    links = set()

    # Find articles in different formats
    # 1. Standard articles
    article_elements = soup.find_all(['article', 'div'], class_=lambda c: c and ('item' in str(c).lower() or 'td-module' in str(c).lower()))

    for article in article_elements:
        # Find links in headings (h1, h2, h3, h4)
        heading_tags = article.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in heading_tags:
            link = heading.find('a')
            if link and 'href' in link.attrs:
                href = link['href']
                title = link.get_text(strip=True)

                if 'poskok.info' in href and '/category/' not in href and '/tag/' not in href:
                    # Check blacklist
                    if not is_blacklisted(href, title):
                        links.add(href)

    # 2. Additionally, find all links in the main content part
    main_content = soup.find('div', id=lambda i: i and 'main-content' in i)
    if main_content:
        content_links = main_content.find_all('a', href=True)
        for link in content_links:
            href = link['href']
            title = link.get_text(strip=True)

            if 'poskok.info' in href and '/category/' not in href and '/tag/' not in href:
                # Check if the link leads to an article
                if any(segment in href for segment in ['2023/', '2024/', '2022/', '.html']):
                    # Check blacklist
                    if not is_blacklisted(href, title):
                        links.add(href)

    logger.info(f"Found {len(links)} links on {category_url}")
    return list(links)

def get_all_category_links(category_url, max_pages=300):
    """Gets all article links from a category, including pagination."""
    all_links = set()
    page_num = 1
    consecutive_empty_pages = 0
    base_url = category_url.rstrip('/')

    while page_num <= max_pages and consecutive_empty_pages < 2:
        # Form URL for current category page
        if page_num == 1:
            current_url = f"{base_url}/"
        else:
            current_url = f"{base_url}/page/{page_num}/"

        logger.info(f"Getting links from: {current_url}")

        article_links = get_article_links(current_url)

        if not article_links:
            consecutive_empty_pages += 1
            logger.warning(f"No links found on page {page_num}. Empty response #{consecutive_empty_pages}")
        else:
            consecutive_empty_pages = 0
            existing_count = len(all_links)
            all_links.update(article_links)
            new_count = len(all_links) - existing_count
            logger.info(f"Added {new_count} new links (total {len(all_links)})")

        # Add pause between requests to avoid blocking
        delay = random.uniform(2.0, 4.0)
        time.sleep(delay)
        page_num += 1

    return list(all_links)

def get_year_archive_links(base_url, start_year=2012, end_year=2024):
    """Gets article links from archives by years and months."""
    all_archive_links = []
    current_year = datetime.now().year

    # If end_year is greater than current year, use current year
    if end_year > current_year:
        end_year = current_year

    # Iterate through years (from oldest to newest)
    for year in range(start_year, end_year + 1):
        logger.info(f"\nSearching archive for year: {year}")

        # For each year, iterate through months (1-12)
        for month in range(1, 13):
            # Skip future months in current year
            if year == current_year and month > datetime.now().month:
                continue

            month_url = f"{base_url}/{year}/{month:02d}/"
            logger.info(f"Getting archive for: {month_url}")

            # Get links from first page of month
            month_links = get_article_links(month_url)

            if month_links:
                all_archive_links.extend(month_links)
                logger.info(f"Found {len(month_links)} articles for {year}/{month:02d}")

                # Check pagination for month
                page_num = 2
                consecutive_empty_pages = 0

                while consecutive_empty_pages < 2 and page_num <= 20:  # Limited to 20 pages per month
                    paginated_url = f"{month_url}page/{page_num}/"
                    logger.info(f"Getting page {page_num} for month {year}/{month:02d}")

                    page_links = get_article_links(paginated_url)

                    if not page_links:
                        consecutive_empty_pages += 1
                    else:
                        consecutive_empty_pages = 0
                        all_archive_links.extend(page_links)
                        logger.info(f"Found {len(page_links)} articles on page {page_num}")

                    # Pause between requests
                    delay = random.uniform(2.0, 4.0)
                    time.sleep(delay)
                    page_num += 1
            else:
                logger.info(f"No articles found for {year}/{month:02d}")

            # Pause between months
            time.sleep(random.uniform(1.0, 3.0))

    # Remove duplicates
    return list(set(all_archive_links))

def save_links_to_file(links, output_folder, filename="all_links.json"):
    """Saves all found links to a JSON file."""
    # Ensure the full path to the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Create the full file path
    links_file = os.path.join(output_folder, filename)
    
    # Log the exact path where we're saving
    logger.info(f"Saving {len(links)} links to file: {links_file}")
    
    # Save the links
    with open(links_file, 'w', encoding='utf-8') as f:
        json.dump(list(links), f, ensure_ascii=False)
    
    logger.info(f"Successfully saved {len(links)} links to {filename}")
    
    # Also divide the links into batches here directly
    batches_dir = os.path.join(os.path.dirname(output_folder), "link_batches")
    divide_links_into_batches(links, batches_dir, batch_size=1000)
    
    return links_file

def load_links_from_file(output_folder, filename="all_links.json"):
    """Loads links list from a JSON file."""
    links_file = os.path.join(output_folder, filename)
    try:
        with open(links_file, 'r', encoding='utf-8') as f:
            return list(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info(f"No links file found: {filename}")
        return []

def setup_category_mapping():
    """Prepares expanded mapping of categories for all sections of the portal."""
    return {
        "Novice": "https://poskok.info/category/aktualno/",
        "Društvo": "https://poskok.info/category/drustvo/",
        "Monty Dayton": "https://poskok.info/category/monty-dayton/",
        "Ex Yu": "https://poskok.info/category/ex-yu/",
        "Hrvatska": "https://poskok.info/category/perecija/",
        "Svijet": "https://poskok.info/category/svijet/",
        "Kolumne": "https://poskok.info/category/kolumne/",
        "Sport": "https://poskok.info/category/sport/",
        "Religija": "https://poskok.info/category/religija/",
        "Kultura": "https://poskok.info/category/kultura/",
        "Gospodarstvo": "https://poskok.info/category/gospodarstvo/",
        "Crna kronika": "https://poskok.info/category/crna-kronika/",
        "Lifestyle": "https://poskok.info/category/lifestyle/",
        "Politika": "https://poskok.info/category/politika/",
        "Dijaspora": "https://poskok.info/category/dijaspora/",
        "Zdravlje": "https://poskok.info/category/zdravlje/",
        "Obrazovanje": "https://poskok.info/category/obrazovanje/",
        "Tehnologija": "https://poskok.info/category/tech/"
    }

def load_config():
    """Loads or creates default configuration for scraping."""
    config_path = "scraping_config.json"

    # Default settings
    default_config = {
        "start_year": 2012,  # Starting year of archive (set to portal's beginning year)
        "end_year": datetime.now().year,  # Current year
        "max_pages_per_category": 300,  # Number of pages per category
        "categories": list(setup_category_mapping().keys()),  # All categories
        "scrape_archive": True,  # Scrape yearly archive
        "force_refresh_links": False  # Force refresh of links
    }

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            # Fill in missing parameters with default values
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info(f"Creating new configuration")
        config = default_config
        # Save configuration for future use
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    # Print active configuration
    logger.info("Active configuration:")
    for key, value in config.items():
        if key == "categories" and len(value) > 5:
            logger.info(f"  {key}: {len(value)} categories")
        else:
            logger.info(f"  {key}: {value}")

    return config

def divide_links_into_batches(links, output_dir, batch_size=1000):
    """Divides links into batches and saves them."""
    logger.info(f"Dividing {len(links)} links into batches of {batch_size}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Clear any existing batch files
    for file in os.listdir(output_dir):
        if file.startswith("links_batch_") and file.endswith(".json"):
            os.remove(os.path.join(output_dir, file))
    
    # Create batches
    batches = []
    for i in range(0, len(links), batch_size):
        batch = links[i:i+batch_size]
        batch_file = os.path.join(output_dir, f"links_batch_{i//batch_size+1}.json")
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False)
        
        batches.append(batch_file)
        logger.info(f"Saved batch {i//batch_size+1} with {len(batch)} links to {batch_file}")
    
    # Create an index file for convenience
    index_file = os.path.join(output_dir, "batch_index.json")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_links": len(links),
            "batch_size": batch_size,
            "total_batches": len(batches),
            "batches": batches
        }, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Created {len(batches)} batches in {output_dir}")
    return batches

def main():
    # Base URL of portal
    base_url = "https://poskok.info"

    # Create folder for scraped data
    output_folder = "PoskokData"
    os.makedirs(output_folder, exist_ok=True)

    # Load configuration
    config = load_config()

    # Print information about scope
    logger.info(f"==== SCRAPING SETTINGS ====")
    logger.info(f"Maximum number of pages per category: {config.get('max_pages_per_category', 300)}")
    logger.info(f"Year range for archive: {config.get('start_year', 2012)} - {config.get('end_year', datetime.now().year)}")

    # Check if we need to refresh links
    existing_links = load_links_from_file(output_folder)
    if existing_links and not config.get('force_refresh_links', False):
        logger.info(f"Loaded {len(existing_links)} existing links from archive.")
        links = existing_links
    else:
        # If we don't have links or want to refresh, start collecting
        logger.info("=== Starting link collection phase ===")
        links = []

        # Create category mapping
        category_mapping = setup_category_mapping()

        # 1. First get articles from the homepage
        logger.info("\n--- Getting articles from homepage ---")
        homepage_links = get_homepage_links(base_url)
        links.extend(homepage_links)
        logger.info(f"Total found {len(homepage_links)} links on homepage")

        # 2. Then get articles from main categories
        categories_to_process = config.get('categories', list(category_mapping.keys()))
        max_pages_per_category = config.get('max_pages_per_category', 50)

        for category_name in categories_to_process:
            category_url = category_mapping.get(category_name)
            if not category_url:
                logger.warning(f"Category {category_name} has no defined URL. Skipping.")
                continue

            logger.info(f"\n--- Getting links for category: {category_name} ({category_url}) ---")
            category_links = get_all_category_links(category_url, max_pages=max_pages_per_category)
            links.extend(category_links)
            logger.info(f"Total found {len(category_links)} articles in category {category_name}")

            # Pause between categories
            if category_name != categories_to_process[-1]:
                delay = random.uniform(3.0, 6.0)
                logger.info(f"Pause of {delay:.2f} seconds before next category")
                time.sleep(delay)

        # 3. Get articles from yearly archive
        start_year = config.get('start_year', 2012)
        end_year = config.get('end_year', datetime.now().year)

        if config.get('scrape_archive', True):
            logger.info(f"\n--- Getting articles from archive by years ({start_year}-{end_year}) ---")
            archive_links = get_year_archive_links(base_url, start_year, end_year)
            logger.info(f"Total found {len(archive_links)} articles in archive")
            links.extend(archive_links)

        # Remove duplicates and filter obvious foreign links
        links = list(set(links))

        # Expanded list of foreign markers in URL for filtering
        foreign_url_patterns = [
            '/en/', '/eng/', '/english/', '/in-english/', 'in-english',
            '/it/', '/ita/', '/italian/', '/italiano/',
            'italia-allo-specchio', 'femminicidio', 'civiltà-nell', 'epicentro-dell',  # Italian article
            'too-hot-to-be', 'declared-undesirable', 'persona-non-grata',  # English article
            'helicopter-crashes', 'hudson-river', 'new-york',  # English article
            'james-carville', 'trump-will', 'martial-law',  # English article
            'lets-call-it', 'move-of-exposed', 'desperate-men', 'germany-bans',  # English article
            'no-joint-for-mile'  # English article
        ]

        # Filter links that shouldn't be part of the results
        filtered_links = []
        for link in links:
            if '/author/' in link or '/tag/' in link or 'poskok.info' not in link:
                continue

            # Check if link is blacklisted
            if is_blacklisted(link):
                continue

            # Check if link contains any obvious foreign marker
            if any(pattern in link.lower() for pattern in foreign_url_patterns):
                continue

            filtered_links.append(link)

        logger.info(f"\nTotal unique links for scraping after filtering: {len(filtered_links)}")

        # Save all links to file
        save_links_to_file(filtered_links, output_folder)
        links = filtered_links

    # Divide links into smaller batches for parallel processing
    divide_links_into_batches(links, "PoskokData/link_batches", batch_size=1000)
    
    logger.info("Link collection complete!")

if __name__ == "__main__":
    main()
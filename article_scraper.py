#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Article Scraper for Poskok Scraper
---------------------------------
Scrapes individual articles from poskok.info based on provided links.
Handles article content extraction and foreign language detection.
"""

from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re
import os
import time
import random
import json
import logging
import argparse
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
    STANDARD_CATEGORIES, CATEGORY_MAP, BLACKLISTED_URLS, BLACKLISTED_TERMS,
    BLACKLISTED_SUBTITLES, ITALIAN_INDICATORS, ENGLISH_INDICATORS,
    STRONG_ITALIAN_PHRASES, STRONG_ENGLISH_PHRASES, USER_AGENTS, DEFAULT_CONFIG
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

def save_progress(processed_urls, output_folder):
    """Saves a list of already processed URLs for continuing work."""
    progress_file = os.path.join(output_folder, 'progress.json')
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(list(processed_urls), f, ensure_ascii=False)
    logger.info(f"Progress saved: {len(processed_urls)} processed URLs")

def load_progress(output_folder):
    """Loads a list of already processed URLs."""
    progress_file = os.path.join(output_folder, 'progress.json')
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("No progress found. Starting new scraping.")
        return set()

def standardize_category(raw_category, url):
    """
    Enhanced function for converting category to one of the standard portal categories.
    Improved detection of categories from URL and text.
    """
    # If we don't have a category, try to extract it from URL
    if not raw_category:
        return extract_category_from_url(url)

    # First check if it's already a standard category
    if raw_category in STANDARD_CATEGORIES:
        return raw_category

    # Special treatment for cases when category contains multiple words separated by commas or 'i'
    if ',' in raw_category or ' i ' in raw_category:
        categories = re.split(r',|\si\s', raw_category)
        # Take the first category that can be mapped to standard
        for cat in categories:
            cat_clean = cat.strip()
            if cat_clean in STANDARD_CATEGORIES:
                return cat_clean
            # Try to find the most similar category
            std_cat = find_similar_category(cat_clean)
            if std_cat != "Novice":  # If it's not the default category
                return std_cat

    # This is enhanced logic for recognizing categories
    # First try to find direct mapping
    raw_lower = raw_category.lower().strip()

    # Expanded mappings of specific category names
    specific_mappings = {
        'aktualno': 'Novice',
        'aktuelno': 'Novice',
        'politika': 'Politika',
        'vijesti': 'Novice',
        'društvo': 'Društvo',
        'drustvo': 'Društvo',
        'hrvati': 'Hrvatska',
        'hrvatska': 'Hrvatska',
        'regija': 'Ex Yu',
        'regioni': 'Ex Yu',
        'region': 'Ex Yu',
        'bih': 'Novice',
        'bosna': 'Novice',
        'hercegovina': 'Novice',
        'život': 'Lifestyle',
        'zivot': 'Lifestyle',
        'kultura': 'Kultura',
        'umjetnost': 'Kultura',
        'kolumna': 'Kolumne',
        'komentar': 'Kolumne',
        'monty': 'Monty Dayton',
        'dayton': 'Monty Dayton',
        'sport': 'Sport',
        'nogomet': 'Sport',
        'košarka': 'Sport',
        'rukomet': 'Sport',
        'tenis': 'Sport',
        'vjera': 'Religija',
        'religija': 'Religija',
        'crkva': 'Religija',
        'gospodarstvo': 'Gospodarstvo',
        'ekonomija': 'Gospodarstvo',
        'biznis': 'Gospodarstvo',
        'financije': 'Gospodarstvo',
        'crna kronika': 'Crna kronika',
        'crna': 'Crna kronika',
        'kriminal': 'Crna kronika',
        'lifestyle': 'Lifestyle',
        'stil života': 'Lifestyle',
        'zdravlje': 'Zdravlje',
        'medicina': 'Zdravlje',
        'dijaspora': 'Dijaspora',
        'iseljenistvo': 'Dijaspora',
        'iseljenici': 'Dijaspora',
        'obrazovanje': 'Obrazovanje',
        'škola': 'Obrazovanje',
        'fakultet': 'Obrazovanje',
        'tehnologija': 'Tehnologija',
        'tech': 'Tehnologija',
        'it': 'Tehnologija'
    }

    # Check direct mapping of category
    for key, value in specific_mappings.items():
        if key == raw_lower:
            return value

    # Check substring in category
    for key, value in specific_mappings.items():
        if key in raw_lower:
            return value

    # If we still haven't found a category, try from URL
    url_category = extract_category_from_url(url)
    if url_category != "Novice":  # If we got something more specific than default from URL
        return url_category

    # Default if we can't determine
    return "Novice"

def extract_category_from_url(url):
    """
    Enhanced function for detecting category from article URL.
    """
    # Check URL for known categories
    url_lower = url.lower()

    # First, check direct mapping from URL segments (expanded)
    for url_part, category in CATEGORY_MAP.items():
        pattern = f'/{url_part}/'
        if pattern in url_lower:
            return category

    # Special cases where the category can be found in other parts of the URL
    # Check for sports articles
    sport_terms = ['nogomet', 'kosarka', 'rukomet', 'tenis', 'olimpij', 'sport']
    for term in sport_terms:
        if term in url_lower:
            return "Sport"

    # Check for religious/religious themes
    religion_terms = ['crkva', 'religij', 'vjera', 'biskup', 'papa', 'islam', 'dzamij']
    for term in religion_terms:
        if term in url_lower:
            return "Religija"

    # Check for political themes
    politics_terms = ['politika', 'izbori', 'stranka', 'sabor', 'vlada', 'ministar', 'predsjednik']
    for term in politics_terms:
        if term in url_lower:
            return "Politika"

    # Check for economic themes
    economy_terms = ['ekonomij', 'gospodar', 'financij', 'biznis', 'trzist', 'novac']
    for term in economy_terms:
        if term in url_lower:
            return "Gospodarstvo"

    # Check for crime chronicles
    crime_terms = ['kriminal', 'ubojstv', 'nesrec', 'sudjen', 'zatvor', 'policij', 'uhicen']
    for term in crime_terms:
        if term in url_lower:
            return "Crna kronika"

    # Check for diaspora themes
    diaspora_terms = ['dijaspor', 'iseljenici', 'iseljenistvo', 'inozemst']
    for term in diaspora_terms:
        if term in url_lower:
            return "Dijaspora"

    # Default if nothing succeeds
    return "Novice"

def find_similar_category(raw_category):
    """
    Finds the most similar standard category for the given text.
    """
    if not raw_category:
        return "Novice"

    raw_lower = raw_category.lower()

    # Define some rules for mapping
    mappings = {
        # News and politics
        ('vijest', 'novost', 'aktualn', 'dnevn', 'najnovij'): 'Novice',
        ('polit', 'stranka', 'vlada', 'predsjednik', 'ministar', 'izbor', 'glasanj', 'glasov', 'parlament'): 'Politika',

        # Regions and areas
        ('hrvat', 'split', 'zagreb', 'dalmat', 'slavonij'): 'Hrvatska',
        ('bosn', 'hercegovin', 'mostar', 'sarajev', 'banja', 'luka'): 'Novice',
        ('srb', 'crn', 'gora', 'makedon', 'sever', 'macedon', 'kosov', 'albanij'): 'Ex Yu',
        ('svijet', 'global', 'međunarod', 'eu', 'europ', 'amerika', 'sad', 'kina', 'rusij'): 'Svijet',
        ('dijas', 'iseljeni'): 'Dijaspora',

        # Thematic areas
        ('društv', 'soci', 'zajedn'): 'Društvo',
        ('sport', 'nogomet', 'košark', 'rukomet', 'tenis', 'olimp'): 'Sport',
        ('vjer', 'relig', 'crkv', 'katol', 'pravosl', 'islam'): 'Religija',
        ('ekonom', 'gospodar', 'financ', 'biznis', 'tržišt', 'novac'): 'Gospodarstvo',
        ('krim', 'uboj', 'nesreć', 'sud', 'zatvor', 'polic', 'uhić'): 'Crna kronika',
        ('život', 'stil', 'moda', 'ljepot', 'trend', 'brak', 'obitelj'): 'Lifestyle',
        ('zdrav', 'medicin', 'liječn', 'bolesn', 'virus', 'bolnica', 'covid'): 'Zdravlje',
        ('obraz', 'škol', 'fakult', 'znanj', 'učen', 'student'): 'Obrazovanje',
        ('kult', 'umjetn', 'film', 'književ', 'glazb', 'kazališ'): 'Kultura',
        ('teh', 'digital', 'kompjut', 'internet', 'mobitel', 'gadget'): 'Tehnologija',
        ('kolumn', 'komentar', 'miš', 'osvrt', 'analiz'): 'Kolumne',
        ('monty', 'dayton'): 'Monty Dayton'
    }

    # Go through all rules and check for match
    for terms, category in mappings.items():
        for term in terms:
            if term in raw_lower:
                return category

    # Default category
    return "Novice"

def is_blacklisted(url, title=None):
    """Enhanced checking of blocked content based on URL and title."""

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
        if english_word_count >= 3:  # If there are 3 or more English words, it's probably an English article
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

def is_foreign_by_html_metadata(soup):
    """Detects foreign content based on HTML metadata"""

    # Check HTML lang attribute
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        lang = html_tag.get('lang').lower()
        # Accept only hr, bs, sr
        if lang not in ['hr', 'bs', 'sr']:
            logger.info(f"Foreign language detected through HTML lang attribute: {html_tag.get('lang')}")
            return True

    # Check page title for foreign terms
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()

        # Check for Italian indicators
        italian_terms = ['italia', 'dello', 'della', 'specchio', 'femminicidio', 'civiltà', 'epicentro']
        italian_count = sum(1 for term in italian_terms if term in title_text)
        if italian_count >= 2:
            logger.info(f"Italian content detected in page title: {title_tag.string}")
            return True

        # Check for English indicators
        english_terms = ['too hot', 'declared', 'undesirable', 'persona non grata',
                        'helicopter', 'crashes', 'new york', 'hudson', 'killing',
                        'james', 'carville', 'trump', 'martial', 'law', 'elections']
        english_count = sum(1 for term in english_terms if term in title_text)
        if english_count >= 1:  # Stricter criteria for English
            logger.info(f"English content detected in page title: {title_tag.string}")
            return True

    # Check body class for Italian/English terms
    body_tag = soup.find('body')
    if body_tag and body_tag.get('class'):
        body_classes = ' '.join(body_tag.get('class'))
        for term in BLACKLISTED_TERMS:
            if term.replace(' ', '-') in body_classes:
                logger.info(f"Foreign language detected in body class: {term}")
                return True

    return False

def get_page_content(url, max_retries=5, retry_delay=5, timeout=45):
    """Gets page content with retry mechanism."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=timeout)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:  # Does not exist
                logger.warning(f"Page does not exist (404): {url}")
                return None
            elif response.status_code == 403:  # Access forbidden
                logger.warning(f"Access forbidden (403): {url}")
                time.sleep(retry_delay * 2)  # Longer pause for 403
            else:
                logger.warning(f"Attempt {attempt+1}/{max_retries}: Status code {response.status_code} for {url}")
                time.sleep(retry_delay)
        except requests.exceptions.Timeout:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Timeout for {url}")
            time.sleep(retry_delay)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Connection problem for {url}")
            time.sleep(retry_delay * 2)  # Longer pause for connection problems
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries}: Error {str(e)} for {url}")
            time.sleep(retry_delay)

    logger.error(f"Failed to retrieve after {max_retries} attempts: {url}")
    return None

def is_foreign_language(title, content):
    """
    Enhanced detection of content in a foreign language.
    Returns True if the content is probably in a language other than Bosnian/Croatian/Serbian.
    """
    # Skip empty content
    if not content or content == "N/A":
        return False

    # Initialize counters
    foreign_word_count = 0
    total_words = 0

    # Combined foreign indicators
    foreign_indicators = ITALIAN_INDICATORS + ENGLISH_INDICATORS

    # NEW CHECK: Direct detection of English articles by keywords and phrases
    if title:
        title_lower = title.lower()
        # Check English keywords in title
        english_title_indicators = ['helicopter', 'crashes', 'new york', 'hudson', 'river',
                                  'james', 'carville', 'trump', 'martial', 'law', 'killing',
                                  'aboard', 'no joint for', 'let\'s call', 'move of']

        for indicator in english_title_indicators:
            if indicator in title_lower:
                logger.info(f"English keyword detected in title: {indicator} in '{title}'")
                return True

    # ENHANCED CHECK for English phrases in content
    content_lower = content.lower()
    for phrase in STRONG_ENGLISH_PHRASES:
        if phrase in content_lower:
            logger.info(f"Strong English phrase detected in content: '{phrase}'")
            return True

    # First check title (high weight)
    if title:
        title_words = title.lower().split()
        title_foreign_count = sum(1 for word in title_words if word in foreign_indicators)
        if title_foreign_count >= 2 or (title_foreign_count > 0 and len(title_words) < 5):
            logger.info(f"Foreign language detected in title: {title} ({title_foreign_count} foreign words)")
            return True

    # Check content
    # First divide into words and normalize
    words = content.lower().split()
    total_words = len(words)

    # Count foreign words
    for word in words:
        # Clean word from punctuation
        clean_word = word.strip('.,!?:;-—"\'()')
        if clean_word in foreign_indicators:
            foreign_word_count += 1

    # Calculate percentage of foreign words
    if total_words > 0:
        foreign_percentage = (foreign_word_count / total_words) * 100

        # Threshold: if more than 8% of words are from our list of foreign words, it's probably a foreign language
        if foreign_percentage > 8:
            logger.info(f"Foreign language detected in content: {foreign_percentage:.2f}% foreign words ({foreign_word_count}/{total_words})")
            return True

        # Additional check: if we have at least 15 foreign words, regardless of percentage
        if foreign_word_count >= 15:
            logger.info(f"High number of foreign words: {foreign_word_count} foreign words")
            return True

    # Check specific phrases that strongly indicate content in a foreign language
    for phrase in STRONG_ITALIAN_PHRASES + STRONG_ENGLISH_PHRASES:
        if phrase in content.lower():
            logger.info(f"Strong foreign phrase detected: '{phrase}'")
            return True

    # Additional check: consecutive foreign words
    words = content.lower().split()
    consecutive_foreign = 0
    max_consecutive_foreign = 0

    for word in words:
        clean_word = word.strip('.,!?:;-—"\'()')
        if clean_word in foreign_indicators:
            consecutive_foreign += 1
            max_consecutive_foreign = max(max_consecutive_foreign, consecutive_foreign)
        else:
            consecutive_foreign = 0

    # If we find 3 or more consecutive foreign words, it's probably foreign text
    if max_consecutive_foreign >= 3:
        logger.info(f"Consecutive foreign words detected: {max_consecutive_foreign} words in a row")
        return True

    return False

def parse_date(date_text):
    """Parses date from various formats."""
    if not date_text:
        return None

    # Clean text from extra spaces and special characters
    cleaned_text = date_text.strip()

    # Special processing for Croatian month names
    hr_month_map = {
        'siječnja': '01', 'veljače': '02', 'ožujka': '03', 'travnja': '04',
        'svibnja': '05', 'lipnja': '06', 'srpnja': '07', 'kolovoza': '08',
        'rujna': '09', 'listopada': '10', 'studenog': '11', 'prosinca': '12'
    }

    for hr_month, month_num in hr_month_map.items():
        if hr_month in cleaned_text.lower():
            # Extract day and year from text
            day_match = re.search(r'(\d+)\.?\s+' + hr_month, cleaned_text.lower())
            year_match = re.search(r'\d{4}', cleaned_text)

            if day_match and year_match:
                day = day_match.group(1).zfill(2)
                year = year_match.group(0)
                return datetime(int(year), int(month_num), int(day))

    # Standard date formats
    date_formats = [
        '%d/%m/%Y',       # 21/04/2023
        '%d.%m.%Y',       # 21.04.2023
        '%d.%m.%Y.',      # 21.04.2023.
        '%d %B, %Y',      # 21 April, 2023
        '%d %b %Y',       # 21 Apr 2023
        '%B %d, %Y',      # April 21, 2023
        '%Y-%m-%d'        # 2023-04-21
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(cleaned_text, date_format)
        except ValueError:
            continue

    # If it's not possible to parse the date, try to extract only numbers
    numbers = re.findall(r'\d+', cleaned_text)
    if len(numbers) >= 3:
        try:
            day, month, year = int(numbers[0]), int(numbers[1]), int(numbers[2])
            if year < 100:  # If the year is two-digit
                year += 2000
            return datetime(year, month, day)
        except:
            pass

    logger.warning(f"Unable to parse date: {date_text}")
    return None

def extract_author(soup):
    """Extracts article author."""
    # Method 1: Try to find meta tag for author
    meta_author = soup.find('meta', {'name': 'author'})
    if meta_author and meta_author.get('content'):
        author_name = meta_author.get('content').strip()
        if author_name and author_name.lower() != "poskok.info" and "byposkok" not in author_name.lower():
            return author_name

    # Method 2: Try to find element with class containing "author"
    author_element = soup.find(['span', 'div', 'a'], class_=lambda c: c and 'author' in str(c).lower())
    if author_element:
        author_name = author_element.get_text(strip=True)
        # Remove prefix and "poskok.info" if part of name
        cleaned_name = re.sub(r'^(By|Autor|Piše)[:\s]+', '', author_name, flags=re.IGNORECASE).strip()
        if cleaned_name and cleaned_name.lower() != "poskok.info" and "byposkok" not in cleaned_name.lower():
            return cleaned_name

    # Method 3: Try through "rel" author attribute
    author_rel = soup.find('a', rel='author')
    if author_rel:
        author_name = author_rel.get_text(strip=True)
        if author_name and author_name.lower() != "poskok.info" and "byposkok" not in author_name.lower():
            return author_name

    # Method 4: Try through article structure - often in article footer
    article_footer = soup.find(['footer', 'div'], class_=lambda c: c and ('footer' in str(c).lower() or 'meta' in str(c).lower()))
    if article_footer:
        author_text = None
        # Look for text containing "Autor:" or similar
        for elem in article_footer.find_all(['span', 'div', 'p']):
            text = elem.get_text(strip=True)
            if re.search(r'(autor|piše|by)[:\s]', text, re.IGNORECASE):
                author_text = text
                break

        if author_text:
            # Extract only author name
            author_match = re.search(r'(autor|piše|by)[:\s]+(.+)', author_text, re.IGNORECASE)
            if author_match:
                author_name = author_match.group(2).strip()
                if author_name and author_name.lower() != "poskok.info" and "byposkok" not in author_name.lower():
                    return author_name

    # If no specific author found, return "poskok.info"
    return "poskok.info"

def is_valid_subtitle(text):
    """Checks if subtitle is valid (does not contain blacklisted text)"""
    if not text or len(text) < 10:
        return False

    # Check if it contains any of blacklisted texts
    for phrase in BLACKLISTED_SUBTITLES:
        if phrase in text:
            return False

    # NEW CHECK: Avoid subtitles ending with "..."
    if text.endswith('...') or text.endswith('…'):
        return False

    # NEW CHECK: Avoid subtitles that are too long (probably beginning of article)
    if len(text) > 250:
        return False

    # NEW CHECK: Avoid subtitles that are too specific
    too_specific_patterns = [
        r'\b(kazao je|rekao je|izjavio je|naglasio je|poručio je|zaključio je)\b', # statements
        r'\b(jučer|danas|sutra)\b', # time determinants
        r'\b(međutim|ipak|stoga|zato)\b', # conjunctions that indicate continuation of text
        r'^[A-Z][a-z]+ [A-Z][a-z]+ je', # First and last name at beginning - probably beginning of text
        r'^[A-Z][a-z]+, \d{1,2}\. [a-z]+ \d{4}\.', # Location and date at beginning - probably beginning of text
    ]

    for pattern in too_specific_patterns:
        if re.search(pattern, text):
            return False

    return True

def extract_subtitle(soup):
    """
    Completely new function for extracting subtitle that solves the problem of taking
    the beginning of text as subtitle.
    """
    subtitle_candidates = []

    # 1. First try to find explicitly marked subtitles
    for selector in [
        'div.td-post-sub-title', 'p.td-post-sub-title',
        'div.jeg_post_subtitle', 'p.jeg_post_subtitle',
        'div.excerpt', 'p.excerpt', 'div.sapo', 'p.sapo',
        'h2.subtitle', 'div.subtitle', 'p.subtitle',
        'div.lead', 'p.lead', 'div.summary', 'p.summary'
    ]:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text(strip=True)
            if is_valid_subtitle(text):
                subtitle_candidates.append({"text": text, "source": "direct", "score": 10})

    # 2. Look for meta tags for description
    meta_tags = [
        ('property', 'og:description'),
        ('name', 'description'),
        ('name', 'twitter:description')
    ]

    for attr, value in meta_tags:
        meta = soup.find('meta', {attr: value})
        if meta and meta.get('content'):
            text = meta.get('content').strip()
            # Meta descriptions are often good subtitles
            if is_valid_subtitle(text):
                subtitle_candidates.append({"text": text, "source": "meta", "score": 8})

    # 3. Only after that look at first paragraph
    content_selectors = [
        'div.td-post-content', 'div.tdb-block-inner', 'div.entry-content',
        'div.content-inner', 'div.td-post-text-content', 'article div.td-post-content',
        'div.jeg_post_content', 'div.post-content'
    ]

    for selector in content_selectors:
        content_area = soup.select_one(selector)
        if content_area:
            # Find all paragraphs
            paragraphs = content_area.find_all('p')

            if paragraphs:
                # First paragraph can often be subtitle or introduction
                first_p = paragraphs[0].get_text(strip=True)
                # Second paragraph can be used as subtitle if first one is not good
                second_p = paragraphs[1].get_text(strip=True) if len(paragraphs) > 1 else ""

                # Try to find shorter paragraph that could be subtitle
                if is_valid_subtitle(first_p) and 40 <= len(first_p) <= 200:
                    # Take only first sentence if paragraph is longer than 100 characters
                    if len(first_p) > 100:
                        sentences = re.split(r'[.!?]+', first_p)
                        if sentences and len(sentences[0]) >= 40:
                            first_sentence = sentences[0].strip()
                            subtitle_candidates.append({"text": first_sentence, "source": "first_para_sentence", "score": 6})
                    else:
                        subtitle_candidates.append({"text": first_p, "source": "first_para", "score": 5})

                # If first paragraph is not good, try with second
                elif second_p and is_valid_subtitle(second_p) and 40 <= len(second_p) <= 200:
                    if len(second_p) > 100:
                        sentences = re.split(r'[.!?]+', second_p)
                        if sentences and len(sentences[0]) >= 40:
                            first_sentence = sentences[0].strip()
                            subtitle_candidates.append({"text": first_sentence, "source": "second_para_sentence", "score": 4})
                    else:
                        subtitle_candidates.append({"text": second_p, "source": "second_para", "score": 3})

    # 4. Look for specific elements that could contain subtitle
    intro_p = soup.find('p', class_=lambda c: c and any(term in str(c).lower() for term in ['intro', 'lead', 'summary', 'excerpt', 'subtitle']))
    if intro_p:
        text = intro_p.get_text(strip=True)
        if is_valid_subtitle(text):
            subtitle_candidates.append({"text": text, "source": "intro_p", "score": 7})

    # 5. Try to find subtitle in strong/b elements at beginning of article
    if content_area:
        strong_elems = content_area.find_all(['strong', 'b'])
        for strong in strong_elems[:2]:  # Only first 2 strong elements
            text = strong.get_text(strip=True)
            # Strong elements at beginning often serve as subtitles
            if is_valid_subtitle(text) and 40 <= len(text) <= 200:
                subtitle_candidates.append({"text": text, "source": "strong", "score": 5})

    # Sort candidates by score, then by optimal length
    if subtitle_candidates:
        # Prefer subtitles between 60-150 characters (not too short, not too long)
        subtitle_candidates.sort(key=lambda x: (-x["score"], abs(len(x["text"]) - 100)))

        # Additional check for first choice - does it repeat beginning of text?
        best_candidate = subtitle_candidates[0]["text"]

        # Final cleaning of subtitle
        # Remove shortening/continuing indicators like "..." or "…" at end
        best_candidate = re.sub(r'[.…]+$', '', best_candidate).strip()

        # Add period at end if there's no punctuation
        if best_candidate and not best_candidate[-1] in '.!?':
            best_candidate += '.'

        return best_candidate

    return "N/A"  # If we didn't find a good subtitle

def scrape_article(url, max_retries=5, retry_delay=5, timeout=45):
    """Scrapes a single article and returns its data."""
    logger.info(f"Scraping article: {url}")

    # Immediately check if URL is blacklisted
    if is_blacklisted(url):
        logger.info(f"Skipping URL that is blacklisted: {url}")
        return None

    content = get_page_content(url, max_retries, retry_delay, timeout)
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')

    # NEW CHECK: Detecting language through HTML metadata
    if is_foreign_by_html_metadata(soup):
        logger.info(f"Skipping article with metadata in foreign language: {url}")
        return None

    # Get article title for checking
    title_element = soup.find(['h1', 'h2'], class_=lambda c: c and any(cls in str(c) for cls in ['entry-title', 'td-post-title', 'tdb-title-text']))
    title_text = ""

    if title_element:
        title_text = title_element.get_text(strip=True)

        # Check if title is blacklisted
        if is_blacklisted(url, title_text):
            logger.info(f"Skipping article with title that is blacklisted: {title_text}")
            return None
    else:
        # Alternative way to find title
        title_meta = soup.find('meta', property='og:title')
        if title_meta:
            title_text = title_meta.get('content', '').split('|')[0].strip()

            # Check if title is blacklisted
            if is_blacklisted(url, title_text):
                logger.info(f"Skipping article with title that is blacklisted (meta): {title_text}")
                return None

    # Initialize article data
    article_data = {'url': url, 'title': title_text if title_text else "N/A"}

    # ADDED CHECK: Directly check if article has English title
    if title_text and any(english_term.lower() in title_text.lower() for english_term in [
            "helicopter", "crashes", "new york", "hudson", "river", "killing", "aboard",
            "james", "carville", "trump", "fears", "martial", "law", "elections",
            "let's", "call", "move", "desperate", "men", "germany", "bans", "entry",
            "austria", "considering", "same", "joint", "mile"
        ]):
        logger.info(f"Skipping article with English title: {title_text}")
        return None

    # Get publication date
    date_element = soup.find(['time', 'span', 'div'], class_=lambda c: c and any(cls in str(c) for cls in ['entry-date', 'td-post-date', 'meta-date']))
    if date_element:
        date_text = date_element.get_text(strip=True)
        date_obj = parse_date(date_text)
        if date_obj:
            article_data['date'] = date_obj.strftime('%d.%m.%Y')
        else:
            article_data['date'] = date_text
    else:
        # Alternative way to find date
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta:
            try:
                date_obj = datetime.fromisoformat(date_meta.get('content', '').split('+')[0])
                article_data['date'] = date_obj.strftime('%d.%m.%Y')
            except:
                article_data['date'] = "N/A"
        else:
            article_data['date'] = "N/A"

    # Get article author
    article_data['author'] = extract_author(soup)

    # Get article category - ENHANCED
    raw_category = None

    # 1. Try from breadcrumbs navigation
    breadcrumbs = soup.find('div', class_=lambda c: c and 'breadcrumbs' in str(c).lower())
    if breadcrumbs:
        category_links = breadcrumbs.find_all('a')
        if len(category_links) > 1:  # First link is usually Home/Home page
            raw_category = category_links[1].get_text(strip=True)

    # 2. Try from meta tags
    if not raw_category:
        category_meta = soup.find('meta', property='article:section')
        if category_meta:
            raw_category = category_meta.get('content', '')

    # 3. Look for categories in special elements
    if not raw_category:
        category_elements = soup.find_all(['span', 'a', 'div'], class_=lambda c: c and any(
            term in str(c).lower() for term in ['category', 'cat', 'rubrika', 'kategorija']))

        for element in category_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 30:  # Avoid too long texts
                raw_category = text
                break

    # 4. Try from URL
    if not raw_category:
        # First try to get category directly from URL
        url_category = extract_category_from_url(url)
        if url_category != "Novice":  # If we didn't get default category
            article_data['category'] = url_category
        else:
            category_match = re.search(r'poskok\.info/(?:category/)?([^/]+)/', url)
            if category_match:
                category = category_match.group(1)
                # Map known URL categories to human-readable names
                raw_category = CATEGORY_MAP.get(category, category.replace('-', ' ').title())

    # 5. Look for keywords in title or content to determine category
    if not raw_category and title_text:
        title_lower = title_text.lower()
        # Check keywords in title
        keywords_categories = {
            ('nogomet', 'košark', 'nba', 'liga', 'utakmic', 'pobjed', 'poraz', 'igra', 'trener'): 'Sport',
            ('crkv', 'papa', 'biskup', 'religij', 'vjera', 'župnik', 'misa', 'hodočašć'): 'Religija',
            ('ekonomij', 'gospodar', 'financij', 'novac', 'cijene', 'inflacij', 'tečaj'): 'Gospodarstvo',
            ('ubojstv', 'zločin', 'kriminal', 'policij', 'uhićen', 'sud', 'zatvor'): 'Crna kronika',
            ('obitelj', 'brak', 'djeca', 'život', 'obrazovan', 'škola', 'fakultet'): 'Društvo'
        }

        for keywords, category in keywords_categories.items():
            if any(keyword in title_lower for keyword in keywords):
                raw_category = category
                break

    # Standardize category into one of the main site categories
    if not article_data.get('category'):  # If category hasn't been set yet
        article_data['category'] = standardize_category(raw_category, url) if raw_category else "Novice"

    # MODIFIED: Using new function to get subtitle
    article_data['subtitle'] = extract_subtitle(soup)

    # ENHANCED: Getting article content
    content_element = None

    # Try to find main article content through different selectors
    content_selectors = [
        'div.td-post-content',
        'div.tdb-block-inner',
        'div.jeg_post_content',
        'div.entry-content',
        'div.td-post-text-content',
        'div.content-inner',
        'article div.td-post-content',
        'div.post-content',
        'div.article-content',
        'div.td_block_wrap',
        'div.content-area',
        'div.main-content'
    ]

    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            content_element = elements[0]
            break

    article_content = ""

    if content_element:
        # IMPROVED: Get all paragraphs from content with less aggressive filtering
        paragraphs = content_element.find_all(['p', 'div', 'h3', 'h4', 'ul', 'ol'])
        article_paragraphs = []

        for p in paragraphs:
            # Skip certain elements that are not part of main text
            if p.find('script') or p.find('iframe') or p.find('blockquote', class_='twitter-tweet'):
                continue

            # Skip if element has class indicating parts that are not article
            if p.get('class') and any(cls in str(p.get('class')) for cls in ['share', 'social', 'comment', 'widget', 'sidebar', 'footer', 'nav']):
                continue

            # Check if paragraph contains only image or embed
            if (p.find('img') or p.find('iframe') or p.find('embed')) and len(p.get_text(strip=True)) < 30:
                continue

            text = p.get_text(strip=True)

            # LESS AGGRESSIVE FILTERING: Accept more text from article
            # Skip only visible ads and short text
            skip_terms = [
                'oglas', 'advertisement', 'reklama', 'sponsored',
                'više na našoj facebook stranici', 'pratite nas na'
            ]

            if text and len(text) > 15 and not any(term in text.lower() for term in skip_terms):
                article_paragraphs.append(text)

        # Join paragraphs into complete article text
        article_content = ' '.join(article_paragraphs)
    else:
        # Alternative approach when we don't find main content element
        all_paragraphs = soup.find_all('p')
        article_paragraphs = []

        for p in all_paragraphs:
            # Check if paragraph is in footer, sidebar or comments
            parent_classes = ' '.join([str(parent.get('class', '')) for parent in p.parents if parent.get('class')])
            if ('footer' in parent_classes or 'sidebar' in parent_classes or
                'comment' in parent_classes or 'widget' in parent_classes or
                'breadcrumb' in parent_classes):
                continue

            text = p.get_text(strip=True)

            # LESS AGGRESSIVE FILTERING: Take more text
            if text and len(text) > 20:
                article_paragraphs.append(text)

        article_content = ' '.join(article_paragraphs)

    # Check if content is empty
    if not article_content or article_content == "":
        logger.warning(f"No article content found: {url}")
        article_data['content'] = "N/A"
        return None
    else:
        article_data['content'] = article_content

    # ADDITIONAL CHECK: For foreign articles, check if there are too many English words
    if article_data.get('content'):
        content_text = article_data.get('content').lower()
        english_count = sum(1 for term in ENGLISH_INDICATORS if term in content_text)

        # If there are too many English indicators, it's probably an English article
        if english_count > 20:  # Increased limit for rejecting English articles
            logger.info(f"Article has too many English words ({english_count}): {title_text}")
            return None

    # Check content language - enhanced version
    if is_foreign_language(article_data.get('title', ''), article_data.get('content', '')):
        logger.info(f"Article is in a foreign language. Skipping: {article_data.get('title', '')}")
        return None

    # Additional check: sample of words from middle of text for foreign language detection
    content_words = article_data.get('content', '').split()
    if len(content_words) > 100:
        middle_index = len(content_words) // 2
        sample = ' '.join(content_words[middle_index:middle_index+50])

        # Check if this sample contains foreign language
        if is_foreign_language('', sample):
            logger.info(f"Foreign language detected in content sample. Skipping article: {article_data.get('title', '')}")
            return None

    return article_data

def format_article_text(article_data):
    """Formats article data into structured text."""

    if not article_data or not article_data.get('title') or article_data.get('content') == "N/A":
        return None

    # ADDED: Additional subtitle check
    subtitle = article_data.get('subtitle', 'N/A')
    # Check for diplomatic forum
    for phrase in BLACKLISTED_SUBTITLES:
        if subtitle and phrase in subtitle:
            subtitle = "N/A"
            break

    # Create content
    content = "<***>\n"
    content += f"NOVINA: poskok.info\n"
    content += f"DATUM: {article_data.get('date', 'N/A')}\n"
    content += f"RUBRIKA: {article_data.get('category', 'N/A')}\n"
    content += f"NADNASLOV: N/A\n"
    content += f"NASLOV: {article_data.get('title', 'N/A')}\n"
    content += f"PODNASLOV: {subtitle}\n"
    content += f"STRANA: {article_data.get('url', 'N/A')}\n"
    content += f"AUTOR(I): {article_data.get('author', 'N/A')}\n\n"
    content += f"{article_data.get('content', '')}\n\n"

    return content

def save_batch_articles(articles, output_folder, batch_num):
    """Saves articles to batch file."""
    if not articles:
        logger.warning("No articles to save in batch.")
        return False

    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, f"PoskokClanci_batch_{batch_num}.txt")
    saved_count = 0

    with open(filepath, 'w', encoding='utf-8') as output_file:
        for article_data in articles:
            article_text = format_article_text(article_data)
            if article_text:
                output_file.write(article_text)
                saved_count += 1

    logger.info(f"Saved {saved_count} articles to batch file {filepath}.")
    return saved_count > 0

def load_links_batch(batch_file):
    """Loads links from batch file."""
    try:
        with open(batch_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading batch file {batch_file}: {str(e)}")
        return []

def process_links_batch(batch_file, output_folder, config):
    """Processes a single batch of links."""
    links = load_links_batch(batch_file)
    if not links:
        logger.warning(f"No links found in batch file {batch_file}")
        return 0
    
    # Setup for batch processing
    batch_num = int(re.search(r'batch_(\d+)', batch_file).group(1)) if re.search(r'batch_(\d+)', batch_file) else 1
    batch_output = os.path.join(output_folder, f"articles_batch_{batch_num}")
    os.makedirs(batch_output, exist_ok=True)
    
    # Load progress for this batch
    processed_urls = load_progress(batch_output)
    remaining_links = [link for link in links if link not in processed_urls]
    logger.info(f"Batch {batch_num}: {len(remaining_links)} links remaining out of {len(links)}")
    
    # Counters for statistics
    processed_count = 0
    success_count = 0
    skipped_foreign_count = 0
    batch_articles = []
    
    # Process links
    for i, url in enumerate(remaining_links):
        logger.info(f"[{i+1}/{len(remaining_links)}] Processing article: {url}")
        
        try:
            article_data = scrape_article(
                url, 
                max_retries=config.get('max_retries', 5),
                retry_delay=config.get('retry_delay', 5),
                timeout=config.get('timeout', 45)
            )
            
            # Add URL to processed even if article is not successfully scraped
            processed_urls.add(url)
            processed_count += 1
            
            # Periodically save progress
            if processed_count % config.get('checkpoint_interval', 20) == 0:
                save_progress(processed_urls, batch_output)
            
            # Skip foreign language articles
            if article_data is None:
                skipped_foreign_count += 1
                continue
            
            if article_data and article_data.get('content') and article_data.get('content') != "N/A":
                # Add article to batch
                batch_articles.append(article_data)
                success_count += 1
                
                # Save batch when we reach batch size
                if len(batch_articles) >= config.get('batch_size', 100):
                    save_batch_articles(batch_articles, batch_output, 1)
                    batch_articles = []  # Reset for next batch
            else:
                logger.warning(f"Article has no content or was not successfully retrieved: {url}")
        
        except Exception as e:
            logger.error(f"Error processing article {url}: {str(e)}")
            # Add URL to processed on error too
            processed_urls.add(url)
        
        # Status report
        if (i + 1) % 10 == 0 or i == len(remaining_links) - 1:
            logger.info(f"Progress: {i+1}/{len(remaining_links)} articles processed ({success_count} successfully, {skipped_foreign_count} skipped as foreign language)")
        
        # Save progress at checkpoints
        if (i + 1) % config.get('checkpoint_interval', 20) == 0:
            save_progress(processed_urls, batch_output)
            logger.info(f"Checkpoint saved. Total processed {len(processed_urls)} URLs.")
        
        # Pause between requests (adaptive)
        delay = random.uniform(1.5, 3.0)
        time.sleep(delay)
    
    # Save remaining articles in last batch
    if batch_articles:
        save_batch_articles(batch_articles, batch_output, 1)
    
    # Final save of progress
    save_progress(processed_urls, batch_output)
    
    logger.info(f"Batch {batch_num} processing complete: {processed_count} articles processed, {success_count} successfully saved, {skipped_foreign_count} skipped as foreign language.")
    return success_count

def main():
    parser = argparse.ArgumentParser(description='Article Scraper for Poskok')
    parser.add_argument('--batch', type=str, help='Process a specific batch file')
    parser.add_argument('--all-batches', action='store_true', help='Process all batches sequentially')
    parser.add_argument('--links', type=str, help='JSON file with links to process')
    parser.add_argument('--output', type=str, default='PoskokData/articles', help='Output folder for articles')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_CONFIG['batch_size'], help='Number of articles per batch')
    parser.add_argument('--config', type=str, default='scraping_config.json', help='Configuration file path')
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info(f"Using default configuration")
        config = DEFAULT_CONFIG
    
    # Override config with command line arguments
    config['batch_size'] = args.batch_size
    config['output_folder'] = args.output
    
    # Create output folder
    os.makedirs(args.output, exist_ok=True)
    
    # Mode selection
    if args.batch:
        # Process a single batch file
        logger.info(f"Processing batch file: {args.batch}")
        process_links_batch(args.batch, args.output, config)
    
    elif args.all_batches:
        # Process all batch files
        logger.info("Processing all batches sequentially")
        batch_dir = "link_batches"
        
        if not os.path.exists(batch_dir):
            logger.error(f"Batch directory not found: {batch_dir}")
            return
        
        # Get batch index if exists
        index_file = os.path.join(batch_dir, "batch_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
                batches = index.get('batches', [])
        else:
            # Otherwise find all batch files
            batches = [os.path.join(batch_dir, f) for f in os.listdir(batch_dir) 
                      if f.startswith('links_batch_') and f.endswith('.json')]
        
        total_batches = len(batches)
        logger.info(f"Found {total_batches} batch files to process")
        
        for i, batch_file in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{total_batches}: {batch_file}")
            process_links_batch(batch_file, args.output, config)
    
    elif args.links:
        # Process a JSON file with links
        logger.info(f"Processing links from file: {args.links}")
        try:
            with open(args.links, 'r', encoding='utf-8') as f:
                links = json.load(f)
                
            processed_urls = load_progress(args.output)
            remaining_links = [link for link in links if link not in processed_urls]
            
            logger.info(f"Found {len(links)} links, {len(remaining_links)} remaining to process")
            
            # Setup counters
            processed_count = 0
            success_count = 0
            skipped_foreign_count = 0
            batch_articles = []
            batch_num = 1
            
            # Process links
            for i, url in enumerate(remaining_links):
                logger.info(f"[{i+1}/{len(remaining_links)}] Processing article: {url}")
                
                try:
                    article_data = scrape_article(url)
                    
                    # Add URL to processed even if article is not successfully scraped
                    processed_urls.add(url)
                    processed_count += 1
                    
                    # Periodically save progress
                    if processed_count % config.get('checkpoint_interval', 20) == 0:
                        save_progress(processed_urls, args.output)
                    
                    # Skip foreign language articles
                    if article_data is None:
                        skipped_foreign_count += 1
                        continue
                    
                    if article_data and article_data.get('content') and article_data.get('content') != "N/A":
                        # Add article to batch
                        batch_articles.append(article_data)
                        success_count += 1
                        
                        # Save batch when we reach batch size
                        if len(batch_articles) >= config.get('batch_size', 100):
                            save_batch_articles(batch_articles, args.output, batch_num)
                            batch_articles = []  # Reset for next batch
                            batch_num += 1
                    
                    # Status report
                    if (i + 1) % 10 == 0 or i == len(remaining_links) - 1:
                        logger.info(f"Progress: {i+1}/{len(remaining_links)} articles processed ({success_count} successfully, {skipped_foreign_count} skipped as foreign language)")
                    
                    # Pause between requests
                    delay = random.uniform(1.5, 3.0)
                    time.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Error processing article {url}: {str(e)}")
                    processed_urls.add(url)
            
            # Save remaining articles in last batch
            if batch_articles:
                save_batch_articles(batch_articles, args.output, batch_num)
            
            # Final save of progress
            save_progress(processed_urls, args.output)
            
            logger.info(f"Processing complete: {processed_count} articles processed, {success_count} successfully saved, {skipped_foreign_count} skipped as foreign language.")
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading links file: {str(e)}")
    
    else:
        logger.error("No action specified. Use --batch, --all-batches, or --links")

if __name__ == "__main__":
    main()
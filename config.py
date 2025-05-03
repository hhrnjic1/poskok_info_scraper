#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Poskok Scraper
------------------------------------
Contains all constants, mappings, and blacklists used across scraper components.
"""

# Standard categories from the portal - EXPANDED for better categorization
STANDARD_CATEGORIES = [
    "Novice", "Društvo", "Monty Dayton", "Ex Yu",
    "Hrvatska", "Svijet", "Kolumne", "Sport", "Religija",
    "Kultura", "Gospodarstvo", "Crna kronika", "Lifestyle",
    "Politika", "Dijaspora", "Zdravlje", "Obrazovanje", "Tehnologija"
]

# Mapping URL parts to standard categories - EXPANDED
CATEGORY_MAP = {
    'aktualno': 'Novice',
    'drustvo': 'Društvo',
    'monty-dayton': 'Monty Dayton',
    'ex-yu': 'Ex Yu',
    'perecija': 'Hrvatska',
    'svijet': 'Svijet',
    'kolumne': 'Kolumne',
    'sport': 'Sport',
    'religija': 'Religija',
    'vjera': 'Religija',
    'crkva': 'Religija',
    'kultura': 'Kultura',
    'umjetnost': 'Kultura',
    'gospodarstvo': 'Gospodarstvo',
    'ekonomija': 'Gospodarstvo',
    'financije': 'Gospodarstvo',
    'crna-kronika': 'Crna kronika',
    'crna': 'Crna kronika',
    'kriminal': 'Crna kronika',
    'lifestyle': 'Lifestyle',
    'zivot': 'Lifestyle',
    'zdravlje': 'Zdravlje',
    'medicina': 'Zdravlje',
    'politika': 'Politika',
    'izbori': 'Politika',
    'dijaspora': 'Dijaspora',
    'iseljenistvo': 'Dijaspora',
    'obrazovanje': 'Obrazovanje',
    'skola': 'Obrazovanje',
    'fakultet': 'Obrazovanje',
    'tehnologija': 'Tehnologija',
    'tech': 'Tehnologija'
}

# Explicit list of blacklisted URLs
BLACKLISTED_URLS = [
    "https://poskok.info/italia-allo-specchio-del-femminicidio-il-declino-di-una-civilta-nellepicentro-dellamore/",
    "https://poskok.info/too-hot-to-be-declared-undesirable/",
    "https://poskok.info/helicopter-crashes-into-new-yorks-hudson-river-killing-all-six-aboard/",
    "https://poskok.info/james-carville-fears-trump-will-declare-martial-law-and-rig-the-elections/",
    "https://poskok.info/lets-call-it-a-move-of-exposed-desperate-men-germany-bans-dodiks-entry-austria-considering-the-same/"
]

# Explicit list of blacklisted terms in titles and URLs - EXPANDED
BLACKLISTED_TERMS = [
    # Italian terms
    "italia allo specchio", "femminicidio", "civilta nell", "epicentro dell", "nella terra",
    "della", "dello", "degli", "delle", "nell", "italiano", "italia",
    # English terms
    "too hot to be", "declared undesirable", "persona non grata", "dressed as",
    "in english", "english version", "new york", "hudson river", "helicopter crashes",
    "james carville", "trump will declare", "martial law", "rig the elections",
    "lets call it", "move of exposed", "desperate men", "germany bans",
    "no joint for mile", "helicopter", "crashes",
    # General indicators in URL
    "in-english", "english-version", "italiano", "italian-version"
]

# Blacklist for subtitle - NEW
BLACKLISTED_SUBTITLES = [
    "Na Diplomatskom forumu u Antaliji",
    "Bošnjačka politika svjesna je da",
    "Kažu neki da je Trump Neron"
]

# Detailed indicators of foreign language - EXPANDED
ITALIAN_INDICATORS = [
    'nella', 'dello', 'della', 'degli', 'delle', 'nell', 'italiano', 'italia',
    'civiltà', 'specchio', 'allo', 'epicentro', 'declino', 'femminicidio',
    'una settimana', 'due studentesse', 'questa', 'questo', 'questi', 'queste',
    'come', 'sono', 'dove', 'oggi', 'paese', 'terra', 'essere', 'alla',
    'legge', 'caso', 'più', 'società', 'cultura', 'donne', 'uomini', 'volta',
    'ancora', 'sempre', 'anche', 'quando', 'perché', 'senza', 'tutto', 'tutti',
    'ogni', 'altro', 'altra', 'altri', 'altre', 'quello', 'quella', 'quelli', 'quelle'
]

# EXPANDED English indicators
ENGLISH_INDICATORS = [
    'the', 'that', 'this', 'these', 'those', 'there', 'they', 'them', 'their', 'because',
    'when', 'what', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
    'would', 'could', 'should', 'must', 'might', 'may', 'had', 'been', 'have', 'has',
    'declared', 'undesirable', 'persona non grata', 'too hot', 'dressed as',
    'came', 'forgot', 'woman', 'women', 'just', 'didn', 'wasn', 'doesn', 'aren',
    'don', 'looking', 'asked', 'rolled', 'over', 'know', 'knows', 'knew', 'known',
    'about', 'above', 'across', 'after', 'against', 'along', 'around', 'before', 'behind',
    'below', 'beneath', 'beside', 'between', 'beyond', 'during', 'except', 'inside',
    'outside', 'through', 'under', 'underneath', 'helicopter', 'crashes', 'river', 'york',
    'james', 'trump', 'fears', 'will', 'martial', 'law', 'elections', 'rig', 'move',
    'desperate', 'men', 'germany', 'bans', 'entry', 'austria', 'considering', 'same',
    'joint', 'mile', 'killing', 'aboard'
]

# Strong phrases that indicate foreign language
STRONG_ITALIAN_PHRASES = [
    'nella terra di', 'in una settimana', 'il paese si confronta',
    'la legge per quanto', 'la percezione della donna', 'il caso di',
    'questi episodi non sono', 'civiltà antica', 'pur essendo'
]

# EXPANDED English phrases
STRONG_ENGLISH_PHRASES = [
    'it\'s not that', 'they just got', 'she came as', 'in this part of',
    'what matters is that', 'she wasn\'t here to', 'no one asked',
    'this column contains', 'if you\'re offended', 'may contain traces of',
    'helicopter crashed', 'new york city', 'killing all', 'aboard', 'hudson river',
    'tourist helicopter', 'mayor eric adams', 'declared martial law',
    'james carville fears', 'trump will', 'rig the elections',
    'let\'s call it', 'move of exposed', 'desperate men', 'austria considering',
    'germany bans', 'no joint for mile'
]

# Setting different User-Agent headers to simulate real users
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

# Default scraping configuration
DEFAULT_CONFIG = {
    "start_year": 2012,              # Starting year for archive
    "end_year": 2024,                # Ending year for archive
    "max_pages_per_category": 300,   # Maximum pages to scrape per category
    "batch_size": 100,               # Number of articles per batch file
    "checkpoint_interval": 20,       # How often to save progress
    "max_retries": 5,                # Maximum number of retries for failed requests
    "retry_delay": 5,                # Delay between retries in seconds
    "timeout": 45,                   # Request timeout in seconds
    "scrape_archive": True,          # Whether to scrape the archive
    "force_refresh_links": False,    # Whether to force refreshing links
    "output_folder": "PoskokData"    # Main output folder
}
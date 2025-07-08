#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Link Collector for Poskok Scraper
----------------------------------------
Captures ALL possible links from poskok.info including:
- Archive pages
- Category pages  
- Tag pages
- Author pages
- Search results
- Hidden/unlisted content
- Dynamic/JavaScript loaded content
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
from urllib.parse import urljoin, urlparse
import concurrent.futures

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import from config with fallbacks
try:
    from config import USER_AGENTS
except ImportError:
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    ]

class EnhancedLinkCollector:
    def __init__(self, base_url="https://poskok.info", config=None):
        self.base_url = base_url
        self.config = config or {}
        self.all_links = set()
        self.visited_pages = set()
        self.failed_urls = {}
        self.session = requests.Session()
        self.stats = {
            'pages_visited': 0,
            'links_found': 0,
            'errors': 0,
            'categories_found': set(),
            'tags_found': set(),
            'authors_found': set()
        }
        
    def get_headers(self):
        """Get randomized headers for requests."""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,hr;q=0.3,bs;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
    def get_page_content(self, url, max_retries=5, retry_delay=5, timeout=30):
        """Enhanced page retrieval with better error handling."""
        if url in self.visited_pages:
            return None
            
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=self.get_headers(), timeout=timeout)
                
                if response.status_code == 200:
                    self.visited_pages.add(url)
                    self.stats['pages_visited'] += 1
                    return response.content
                elif response.status_code == 404:
                    logger.warning(f"Page not found (404): {url}")
                    self.failed_urls[url] = '404'
                    return None
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403): {url}")
                    time.sleep(retry_delay * 2)
                else:
                    logger.warning(f"Attempt {attempt+1}/{max_retries}: Status {response.status_code} for {url}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries}: Error {str(e)} for {url}")
                
            time.sleep(retry_delay)
            
        logger.error(f"Failed to retrieve after {max_retries} attempts: {url}")
        self.failed_urls[url] = 'max_retries_exceeded'
        self.stats['errors'] += 1
        return None
        
    def extract_all_links(self, soup, current_url):
        """Extract ALL links from a page, not just article links."""
        found_links = set()
        
        # Find all anchor tags
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Make absolute URL
            absolute_url = urljoin(current_url, href)
            parsed_url = urlparse(absolute_url)
            
            # Only process links from the same domain
            if parsed_url.netloc == urlparse(self.base_url).netloc:
                found_links.add(absolute_url)
                
                # Categorize the link
                if '/category/' in absolute_url:
                    self.stats['categories_found'].add(absolute_url)
                elif '/tag/' in absolute_url:
                    self.stats['tags_found'].add(absolute_url)
                elif '/author/' in absolute_url:
                    self.stats['authors_found'].add(absolute_url)
                    
        return found_links
        
    def discover_hidden_urls(self):
        """Discover URLs through various methods."""
        discovered_urls = set()
        
        # 1. Check robots.txt
        robots_url = urljoin(self.base_url, '/robots.txt')
        try:
            response = self.session.get(robots_url, headers=self.get_headers())
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.startswith('Disallow:') or line.startswith('Allow:'):
                        path = line.split(':', 1)[1].strip()
                        if path and path != '/':
                            discovered_urls.add(urljoin(self.base_url, path))
        except:
            pass
            
        # 2. Check sitemap.xml
        sitemap_urls = [
            urljoin(self.base_url, '/sitemap.xml'),
            urljoin(self.base_url, '/sitemap_index.xml'),
            urljoin(self.base_url, '/post-sitemap.xml'),
            urljoin(self.base_url, '/page-sitemap.xml'),
            urljoin(self.base_url, '/category-sitemap.xml'),
            urljoin(self.base_url, '/sitemap-misc.xml'),
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = self.session.get(sitemap_url, headers=self.get_headers())
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    for loc in soup.find_all('loc'):
                        discovered_urls.add(loc.text)
            except:
                pass
                
        # 3. Common WordPress URLs
        common_paths = [
            '/feed/', '/comments/feed/', '/wp-json/', '/wp-json/wp/v2/posts',
            '/xmlrpc.php', '/wp-login.php', '/wp-admin/', '/wp-content/uploads/',
            '/category/', '/tag/', '/author/', '/search/', '/page/1/'
        ]
        
        for path in common_paths:
            discovered_urls.add(urljoin(self.base_url, path))
            
        logger.info(f"Discovered {len(discovered_urls)} potential URLs through various methods")
        return discovered_urls
        
    def crawl_site_comprehensively(self, max_depth=10):
        """Comprehensive site crawling with depth control."""
        to_visit = {self.base_url: 0}  # URL: depth
        visited = set()
        
        # Add discovered URLs
        discovered = self.discover_hidden_urls()
        for url in discovered:
            to_visit[url] = 1
            
        while to_visit and len(visited) < 100000:  # Safety limit
            current_url, depth = next(iter(to_visit.items()))
            del to_visit[current_url]
            
            if current_url in visited or depth > max_depth:
                continue
                
            logger.info(f"Crawling: {current_url} (depth: {depth})")
            content = self.get_page_content(current_url)
            
            if content:
                visited.add(current_url)
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract all links
                found_links = self.extract_all_links(soup, current_url)
                
                # Add article links to our collection
                for link in found_links:
                    if self.is_article_url(link):
                        self.all_links.add(link)
                        self.stats['links_found'] += 1
                    
                    # Add to crawl queue if not visited
                    if link not in visited and link not in to_visit:
                        to_visit[link] = depth + 1
                        
            # Be polite
            time.sleep(random.uniform(0.5, 2.0))
            
            # Periodic status update
            if len(visited) % 100 == 0:
                logger.info(f"Progress: Visited {len(visited)} pages, found {len(self.all_links)} articles")
                
    def is_article_url(self, url):
        """Enhanced article URL detection."""
        # Patterns that indicate an article
        article_patterns = [
            r'/\d{4}/\d{2}/[^/]+/$',  # Date-based URLs
            r'\.html?$',               # HTML files
            r'/[^/]+-\d+/$',          # Slug with ID
            r'/article/',              # Article path
            r'/post/',                 # Post path
            r'/story/',                # Story path
            r'/news/',                 # News path
        ]
        
        # Patterns to exclude
        exclude_patterns = [
            r'/page/\d+/$',           # Pagination
            r'/category/',            # Categories
            r'/tag/',                 # Tags
            r'/author/',              # Authors
            r'/search/',              # Search
            r'/feed/',                # Feeds
            r'\.xml$',                # XML files
            r'\.pdf$',                # PDF files
            r'/wp-',                  # WordPress system files
        ]
        
        # Check if URL matches article patterns
        for pattern in article_patterns:
            if re.search(pattern, url):
                # Make sure it's not excluded
                for exclude in exclude_patterns:
                    if re.search(exclude, url):
                        return False
                return True
                
        # Additional check: if URL has poskok.info and ends with a slug
        if 'poskok.info' in url and url.endswith('/') and url.count('/') >= 4:
            for exclude in exclude_patterns:
                if re.search(exclude, url):
                    return False
            return True
            
        return False
        
    def collect_all_links(self):
        """Main method to collect all links from the site."""
        logger.info("Starting comprehensive link collection...")
        
        # 1. Crawl the entire site
        self.crawl_site_comprehensively()
        
        # 2. Get archive pages by year/month
        self.collect_archive_links()
        
        # 3. Get all category pages
        self.collect_category_links()
        
        # 4. Get all tag pages
        self.collect_tag_links()
        
        # 5. Get all author pages
        self.collect_author_links()
        
        # 6. Use search to find more content
        self.collect_search_results()
        
        # 7. Check for pagination on all collected pages
        self.check_pagination()
        
        logger.info(f"Collection complete. Total unique article links: {len(self.all_links)}")
        self.print_stats()
        
        return list(self.all_links)
        
    def collect_archive_links(self):
        """Enhanced archive collection."""
        current_year = datetime.now().year
        start_year = self.config.get('start_year', 2012)
        
        for year in range(start_year, current_year + 1):
            for month in range(1, 13):
                # Skip future months
                if year == current_year and month > datetime.now().month:
                    continue
                    
                # Try multiple URL formats
                urls_to_try = [
                    f"{self.base_url}/{year}/{month:02d}/",
                    f"{self.base_url}/archive/{year}/{month:02d}/",
                    f"{self.base_url}/archives/{year}/{month:02d}/",
                    f"{self.base_url}/{year}/{month}/",
                ]
                
                for url in urls_to_try:
                    content = self.get_page_content(url)
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        links = self.extract_all_links(soup, url)
                        
                        for link in links:
                            if self.is_article_url(link):
                                self.all_links.add(link)
                                
                        # Check for pagination
                        self.handle_pagination(soup, url)
                        break
                        
    def collect_category_links(self):
        """Collect all category pages."""
        logger.info("Collecting category links...")
        
        # First, find all categories
        category_urls = list(self.stats['categories_found'])
        
        # Also try common category URL patterns
        common_categories = [
            'novice', 'drustvo', 'politika', 'svijet', 'sport', 'kultura',
            'gospodarstvo', 'lifestyle', 'tehnologija', 'zdravlje', 'obrazovanje'
        ]
        
        for category in common_categories:
            category_urls.append(f"{self.base_url}/category/{category}/")
            category_urls.append(f"{self.base_url}/kategorija/{category}/")
            
        # Process each category
        for category_url in set(category_urls):
            self.process_listing_page(category_url, "category")
                
    def collect_tag_links(self):
        """Collect all tag pages."""
        logger.info("Collecting tag links...")
        
        tag_urls = list(self.stats['tags_found'])
        
        # Process each tag
        for tag_url in tag_urls:
            self.process_listing_page(tag_url, "tag")
            
    def collect_author_links(self):
        """Collect all author pages."""
        logger.info("Collecting author links...")
        
        author_urls = list(self.stats['authors_found'])
        
        # Process each author
        for author_url in author_urls:
            self.process_listing_page(author_url, "author")
            
    def collect_search_results(self):
        """Use search to find additional content."""
        logger.info("Using search to find more content...")
        
        # Common search terms
        search_terms = [
            'a', 'e', 'i', 'o', 'u',  # Vowels to find many results
            '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025',
            'bosna', 'hercegovina', 'sarajevo', 'mostar', 'banja', 'luka',
            'hrvatska', 'srbija', 'slovenija', 'crna', 'gora',
            'politika', 'sport', 'kultura', 'gospodarstvo'
        ]
        
        for term in search_terms:
            search_urls = [
                f"{self.base_url}/?s={term}",
                f"{self.base_url}/search/{term}/",
                f"{self.base_url}/search/?q={term}"
            ]
            
            for search_url in search_urls:
                self.process_listing_page(search_url, "search")
                
    def process_listing_page(self, url, page_type):
        """Process any listing page (category, tag, author, search)."""
        page_num = 1
        consecutive_empty = 0
        
        while consecutive_empty < 3:  # Allow more empty pages
            if page_num == 1:
                current_url = url
            else:
                # Try different pagination formats
                current_url = f"{url}page/{page_num}/"
                if not current_url.endswith('/page/'):
                    current_url = f"{url.rstrip('/')}/page/{page_num}/"
                    
            content = self.get_page_content(current_url)
            
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                links = self.extract_all_links(soup, current_url)
                
                article_count = 0
                for link in links:
                    if self.is_article_url(link):
                        self.all_links.add(link)
                        article_count += 1
                        
                if article_count == 0:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0
                    
                logger.info(f"Found {article_count} articles on {page_type} page {page_num}")
            else:
                consecutive_empty += 1
                
            page_num += 1
            time.sleep(random.uniform(1.0, 3.0))
            
    def handle_pagination(self, soup, base_url):
        """Handle pagination on any page."""
        # Look for pagination elements
        pagination_selectors = [
            '.pagination', '.nav-links', '.page-numbers',
            '.wp-pagenavi', '.paging', '.page-navigation'
        ]
        
        for selector in pagination_selectors:
            pagination = soup.select(selector)
            if pagination:
                # Find all page links
                page_links = pagination[0].find_all('a', href=True)
                for link in page_links:
                    href = urljoin(base_url, link['href'])
                    if href not in self.visited_pages:
                        self.process_listing_page(href, "paginated")
                break
                
    def check_pagination(self):
        """Check all collected article pages for pagination."""
        logger.info("Checking for paginated articles...")
        
        for url in list(self.all_links):
            # Check if article might be paginated
            content = self.get_page_content(url)
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for pagination in articles
                page_links = soup.find_all('a', href=re.compile(r'/\d+/$'))
                for link in page_links:
                    href = urljoin(url, link['href'])
                    if self.is_article_url(href):
                        self.all_links.add(href)
                        
    def print_stats(self):
        """Print collection statistics."""
        logger.info("=== Collection Statistics ===")
        logger.info(f"Pages visited: {self.stats['pages_visited']}")
        logger.info(f"Total article links found: {self.stats['links_found']}")
        logger.info(f"Unique article links: {len(self.all_links)}")
        logger.info(f"Categories found: {len(self.stats['categories_found'])}")
        logger.info(f"Tags found: {len(self.stats['tags_found'])}")
        logger.info(f"Authors found: {len(self.stats['authors_found'])}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        
    def save_results(self, output_file):
        """Save results with detailed metadata."""
        results = {
            'links': list(self.all_links),
            'stats': {
                'pages_visited': self.stats['pages_visited'],
                'links_found': self.stats['links_found'],
                'unique_links': len(self.all_links),
                'categories': len(self.stats['categories_found']),
                'tags': len(self.stats['tags_found']),
                'authors': len(self.stats['authors_found']),
                'errors': self.stats['errors']
            },
            'failed_urls': self.failed_urls,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Results saved to {output_file}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Poskok Link Collector')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file')
    parser.add_argument('--output', type=str, default='enhanced_links.json', help='Output file')
    parser.add_argument('--max-depth', type=int, default=10, help='Maximum crawl depth')
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Create collector
    collector = EnhancedLinkCollector(config=config)
    
    # Collect links
    links = collector.collect_all_links()
    
    # Save results
    collector.save_results(args.output)
    
    logger.info(f"Collection complete. Found {len(links)} unique article links.")

if __name__ == "__main__":
    main()
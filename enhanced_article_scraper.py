#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Article Scraper for Poskok Scraper
-----------------------------------------
Improved article extraction with better error handling and content detection.
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
import traceback
from pathlib import Path

# Enhanced logging with detailed error tracking
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_article_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedArticleScraper:
    def __init__(self, config=None):
        self.config = config or {}
        self.stats = {
            'total_attempted': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'empty_content': 0,
            'foreign_language': 0,
            'error_types': {}
        }
        self.session = requests.Session()
        
    def scrape_article(self, url, max_retries=5, retry_delay=3, timeout=30):
        """Enhanced article scraping with comprehensive error handling."""
        self.stats['total_attempted'] += 1
        logger.info(f"Scraping article: {url}")
        
        article_data = {
            'url': url,
            'title': 'N/A',
            'date': 'N/A',
            'author': 'N/A',
            'category': 'N/A',
            'subtitle': 'N/A',
            'content': 'N/A',
            'metadata': {},
            'error': None
        }
        
        try:
            content = self.get_page_content(url, max_retries, retry_delay, timeout)
            
            if not content:
                article_data['error'] = 'Failed to retrieve page content'
                self.stats['failed_scrapes'] += 1
                return article_data
                
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract all possible article data
            article_data['title'] = self.extract_title(soup, url)
            article_data['date'] = self.extract_date(soup)
            article_data['author'] = self.extract_author(soup)
            article_data['category'] = self.extract_category(soup, url)
            article_data['subtitle'] = self.extract_subtitle(soup)
            article_data['content'] = self.extract_content(soup)
            article_data['metadata'] = self.extract_metadata(soup)
            
            # Validate content
            if not article_data['content'] or article_data['content'] == 'N/A':
                article_data['error'] = 'No content extracted'
                self.stats['empty_content'] += 1
                self.stats['failed_scrapes'] += 1
                
                # Try alternative content extraction
                article_data['content'] = self.extract_content_alternative(soup)
                
                if article_data['content'] and article_data['content'] != 'N/A':
                    article_data['error'] = None
                    self.stats['empty_content'] -= 1
                    self.stats['failed_scrapes'] -= 1
                    self.stats['successful_scrapes'] += 1
            else:
                self.stats['successful_scrapes'] += 1
                
        except Exception as e:
            error_type = type(e).__name__
            article_data['error'] = f"{error_type}: {str(e)}"
            self.stats['failed_scrapes'] += 1
            self.stats['error_types'][error_type] = self.stats['error_types'].get(error_type, 0) + 1
            logger.error(f"Error scraping {url}: {str(e)}")
            logger.debug(traceback.format_exc())
            
        return article_data
        
    def get_page_content(self, url, max_retries, retry_delay, timeout):
        """Enhanced page retrieval with better error handling."""
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,hr;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=headers, timeout=timeout)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.warning(f"Status {response.status_code} for {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt+1} for {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt+1} for {url}")
            except Exception as e:
                logger.warning(f"Error on attempt {attempt+1} for {url}: {str(e)}")
                
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            
        return None
        
    def extract_title(self, soup, url):
        """Enhanced title extraction with multiple fallbacks."""
        # Try multiple selectors
        title_selectors = [
            'h1.entry-title',
            'h1.post-title',
            'h1.td-post-title',
            'h1.tdb-title-text',
            'h1.single-post-title',
            'h1.article-title',
            'article h1',
            '.post-header h1',
            '#main h1',
            'h1'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
                
        # Try meta tags
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title.get('content', '').strip()
            
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Clean up site name from title
            if '|' in title_text:
                return title_text.split('|')[0].strip()
            elif '-' in title_text:
                return title_text.split('-')[0].strip()
            else:
                return title_text
                
        # Last resort: extract from URL
        url_parts = url.rstrip('/').split('/')
        if url_parts:
            last_part = url_parts[-1]
            # Clean up URL slug
            title = last_part.replace('-', ' ').replace('_', ' ')
            return title.title()
            
        return "N/A"
        
    def extract_date(self, soup):
        """Enhanced date extraction with multiple formats."""
        # Try multiple date selectors
        date_selectors = [
            'time[datetime]',
            'time.entry-date',
            'time.published',
            'span.entry-date',
            'span.post-date',
            'span.td-post-date',
            '.meta-date',
            '.post-date',
            '.published',
            'meta[property="article:published_time"]',
            'meta[itemprop="datePublished"]'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            
            if element:
                # Try to get datetime attribute
                if element.get('datetime'):
                    return self.parse_date(element['datetime'])
                    
                # Try to get content attribute (for meta tags)
                if element.get('content'):
                    return self.parse_date(element['content'])
                    
                # Get text content
                if element.get_text(strip=True):
                    return self.parse_date(element.get_text(strip=True))
                    
        # Try to find date in URL
        url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', soup.url if hasattr(soup, 'url') else '')
        if url_date_match:
            year, month, day = url_date_match.groups()
            return f"{day}.{month}.{year}"
            
        return "N/A"
        
    def parse_date(self, date_text):
        """Parse date from various formats."""
        if not date_text:
            return "N/A"
            
        # Clean the date text
        date_text = date_text.strip()
        
        # Try ISO format first
        try:
            dt = datetime.fromisoformat(date_text.replace('Z', '+00:00'))
            return dt.strftime('%d.%m.%Y')
        except:
            pass
            
        # Try various date formats
        formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%d %B %Y',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_text, fmt)
                return dt.strftime('%d.%m.%Y')
            except:
                continue
                
        # Try Croatian month names
        hr_months = {
            'siječnja': '01', 'siječanj': '01',
            'veljače': '02', 'veljača': '02',
            'ožujka': '03', 'ožujak': '03',
            'travnja': '04', 'travanj': '04',
            'svibnja': '05', 'svibanj': '05',
            'lipnja': '06', 'lipanj': '06',
            'srpnja': '07', 'srpanj': '07',
            'kolovoza': '08', 'kolovoz': '08',
            'rujna': '09', 'rujan': '09',
            'listopada': '10', 'listopad': '10',
            'studenog': '11', 'studeni': '11',
            'prosinca': '12', 'prosinac': '12'
        }
        
        for hr_month, month_num in hr_months.items():
            if hr_month in date_text.lower():
                match = re.search(r'(\d{1,2})\.?\s*' + hr_month, date_text.lower())
                if match:
                    day = match.group(1).zfill(2)
                    year_match = re.search(r'(\d{4})', date_text)
                    if year_match:
                        year = year_match.group(1)
                        return f"{day}.{month_num}.{year}"
                        
        return date_text  # Return original if parsing fails
        
    def extract_author(self, soup):
        """Enhanced author extraction."""
        # Try multiple author selectors
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            '.author-name',
            '.post-author',
            '.entry-author',
            'span.author',
            'a[rel="author"]',
            '.byline .author',
            '.post-meta .author'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            
            if element:
                if element.get('content'):
                    return element['content'].strip()
                elif element.get_text(strip=True):
                    author = element.get_text(strip=True)
                    # Clean up author name
                    author = re.sub(r'^(By|Autor|Piše)[:\s]+', '', author, flags=re.IGNORECASE)
                    if author and author.lower() not in ['poskok.info', 'poskok']:
                        return author
                        
        return "poskok.info"
        
    def extract_category(self, soup, url):
        """Enhanced category extraction."""
        # Try multiple category selectors
        category_selectors = [
            'meta[property="article:section"]',
            '.category-name',
            '.post-category',
            '.entry-category',
            'span.category',
            'a[rel="category"]',
            '.post-meta .category',
            '.breadcrumbs a:nth-of-type(2)'
        ]
        
        for selector in category_selectors:
            element = soup.select_one(selector)
            
            if element:
                if element.get('content'):
                    return element['content'].strip()
                elif element.get_text(strip=True):
                    return element.get_text(strip=True)
                    
        # Extract from URL
        url_category = self.extract_category_from_url(url)
        if url_category:
            return url_category
            
        return "Novice"
        
    def extract_category_from_url(self, url):
        """Extract category from URL structure."""
        # Common category patterns in URLs
        category_patterns = {
            '/novice/': 'Novice',
            '/drustvo/': 'Društvo',
            '/politika/': 'Politika',
            '/svijet/': 'Svijet',
            '/sport/': 'Sport',
            '/kultura/': 'Kultura',
            '/gospodarstvo/': 'Gospodarstvo',
            '/lifestyle/': 'Lifestyle',
            '/tehnologija/': 'Tehnologija',
            '/zdravlje/': 'Zdravlje'
        }
        
        for pattern, category in category_patterns.items():
            if pattern in url.lower():
                return category
                
        return None
        
    def extract_subtitle(self, soup):
        """Enhanced subtitle extraction."""
        # Try multiple subtitle selectors
        subtitle_selectors = [
            '.post-subtitle',
            '.entry-subtitle',
            '.article-subtitle',
            '.td-post-sub-title',
            '.jeg_post_subtitle',
            '.excerpt',
            '.lead',
            '.sapo',
            'h2.subtitle',
            'meta[property="og:description"]',
            'meta[name="description"]'
        ]
        
        for selector in subtitle_selectors:
            element = soup.select_one(selector)
            
            if element:
                if element.get('content'):
                    text = element['content'].strip()
                else:
                    text = element.get_text(strip=True)
                    
                if text and len(text) > 20 and len(text) < 300:
                    return text
                    
        return "N/A"
        
    def extract_content(self, soup):
        """Enhanced content extraction with multiple strategies."""
        # Try multiple content selectors
        content_selectors = [
            'div.td-post-content',
            'div.entry-content',
            'div.post-content',
            'div.article-content',
            'div.content-inner',
            'article .content',
            '.post-body',
            '.article-body',
            '#article-content',
            'div[itemprop="articleBody"]'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            
            if element:
                # Extract paragraphs
                paragraphs = element.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol'])
                
                if paragraphs:
                    content_parts = []
                    
                    for p in paragraphs:
                        # Skip empty paragraphs
                        text = p.get_text(strip=True)
                        if not text:
                            continue
                            
                        # Skip common non-content elements
                        if any(skip in text.lower() for skip in ['oglas', 'advertisement', 'share this', 'pratite nas']):
                            continue
                            
                        content_parts.append(text)
                    
                    if content_parts:
                        return ' '.join(content_parts)
                        
        return "N/A"
        
    def extract_content_alternative(self, soup):
        """Alternative content extraction method for difficult pages."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Try to find the main content area
        main_content = None
        
        # Strategy 1: Look for article tag
        article = soup.find('article')
        if article:
            main_content = article
        else:
            # Strategy 2: Look for main content divs
            for selector in ['#main', '#content', '.main-content', '.content-area']:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
                    
        if main_content:
            # Extract all text
            text = main_content.get_text(separator=' ', strip=True)
            
            # Clean up the text
            text = re.sub(r'\s+', ' ', text)
            
            # Remove common footer/header content
            stop_phrases = [
                'Pratite nas na',
                'Pratite Poskok',
                'Copyright',
                'All rights reserved',
                'Sva prava zadržana',
                'Oglas',
                'OGLAS',
                'Advertising'
            ]
            
            for phrase in stop_phrases:
                if phrase in text:
                    text = text.split(phrase)[0]
                    
            # Only return if we have substantial content
            if len(text) > 100:
                return text
                
        return "N/A"
        
    def extract_metadata(self, soup):
        """Extract additional metadata from the page."""
        metadata = {}
        
        # Extract all meta tags
        for meta in soup.find_all('meta'):
            if meta.get('property'):
                metadata[meta['property']] = meta.get('content', '')
            elif meta.get('name'):
                metadata[meta['name']] = meta.get('content', '')
                
        # Extract JSON-LD data if available
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                metadata['json_ld'] = json.loads(json_ld.string)
            except:
                pass
                
        return metadata
        
    def save_article(self, article_data, output_file):
        """Save article in the required format."""
        if not article_data or article_data.get('error'):
            return False
            
        # Format article text
        article_text = "<***>\n"
        article_text += f"NOVINA: poskok.info\n"
        article_text += f"DATUM: {article_data.get('date', 'N/A')}\n"
        article_text += f"RUBRIKA: {article_data.get('category', 'N/A')}\n"
        article_text += f"NADNASLOV: N/A\n"
        article_text += f"NASLOV: {article_data.get('title', 'N/A')}\n"
        article_text += f"PODNASLOV: {article_data.get('subtitle', 'N/A')}\n"
        article_text += f"STRANA: {article_data.get('url', 'N/A')}\n"
        article_text += f"AUTOR(I): {article_data.get('author', 'N/A')}\n\n"
        article_text += f"{article_data.get('content', '')}\n\n"
        
        # Append to output file
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(article_text)
            
        return True
        
    def print_stats(self):
        """Print scraping statistics."""
        logger.info("=== Scraping Statistics ===")
        logger.info(f"Total URLs attempted: {self.stats['total_attempted']}")
        logger.info(f"Successful scrapes: {self.stats['successful_scrapes']}")
        logger.info(f"Failed scrapes: {self.stats['failed_scrapes']}")
        logger.info(f"Empty content: {self.stats['empty_content']}")
        logger.info(f"Foreign language detected: {self.stats['foreign_language']}")
        
        if self.stats['error_types']:
            logger.info("Error breakdown:")
            for error_type, count in self.stats['error_types'].items():
                logger.info(f"  {error_type}: {count}")
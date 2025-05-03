#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content Filter for Poskok Scraper
---------------------------------
Filters and cleans content from scraped articles.
Removes foreign language articles and improves article quality.
"""

import os
import re
import shutil
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

# Import constants for filtering
from config import (
    ITALIAN_INDICATORS, ENGLISH_INDICATORS, 
    STRONG_ITALIAN_PHRASES, STRONG_ENGLISH_PHRASES
)

def is_foreign_language(title, content):
    """
    Detects content in a foreign language.
    Returns True if the content is likely in a language other than Bosnian/Croatian/Serbian.
    """
    # Skip empty content
    if not content or content == "N/A":
        return False

    # Initialize counters
    foreign_word_count = 0
    total_words = 0

    # Combined foreign indicators
    foreign_indicators = ITALIAN_INDICATORS + ENGLISH_INDICATORS

    # Check English keywords in title
    if title:
        title_lower = title.lower()
        english_title_indicators = ['helicopter', 'crashes', 'new york', 'hudson', 'river',
                                   'james', 'carville', 'trump', 'martial', 'law', 'killing',
                                   'aboard', 'no joint for', 'let\'s call', 'move of']

        for indicator in english_title_indicators:
            if indicator in title_lower:
                logger.info(f"English keyword detected in title: {indicator} in '{title}'")
                return True

    # Check for English phrases in content
    content_lower = content.lower()
    for phrase in STRONG_ENGLISH_PHRASES:
        if phrase in content_lower:
            logger.info(f"Strong English phrase detected in content: '{phrase}'")
            return True

    # Check title (high weight)
    if title:
        title_words = title.lower().split()
        title_foreign_count = sum(1 for word in title_words if word in foreign_indicators)
        if title_foreign_count >= 2 or (title_foreign_count > 0 and len(title_words) < 5):
            logger.info(f"Foreign language detected in title: {title} ({title_foreign_count} foreign words)")
            return True

    # Check content
    words = content.lower().split()
    total_words = len(words)

    # Count foreign words
    for word in words:
        clean_word = word.strip('.,!?:;-—"\'()')
        if clean_word in foreign_indicators:
            foreign_word_count += 1

    # Calculate percentage of foreign words
    if total_words > 0:
        foreign_percentage = (foreign_word_count / total_words) * 100

        # Threshold: if more than 8% of words are from our list of foreign words
        if foreign_percentage > 8:
            logger.info(f"Foreign language detected: {foreign_percentage:.2f}% foreign words ({foreign_word_count}/{total_words})")
            return True

        # If we have at least 15 foreign words, regardless of percentage
        if foreign_word_count >= 15:
            logger.info(f"High number of foreign words: {foreign_word_count} foreign words")
            return True

    # Check specific phrases that strongly indicate content in a foreign language
    for phrase in STRONG_ITALIAN_PHRASES + STRONG_ENGLISH_PHRASES:
        if phrase in content.lower():
            logger.info(f"Strong foreign phrase detected: '{phrase}'")
            return True

    # Check for consecutive foreign words
    consecutive_foreign = 0
    max_consecutive_foreign = 0

    for word in words:
        clean_word = word.strip('.,!?:;-—"\'()')
        if clean_word in foreign_indicators:
            consecutive_foreign += 1
            max_consecutive_foreign = max(max_consecutive_foreign, consecutive_foreign)
        else:
            consecutive_foreign = 0

    # 3 or more consecutive foreign words
    if max_consecutive_foreign >= 3:
        logger.info(f"Consecutive foreign words detected: {max_consecutive_foreign} words in a row")
        return True

    return False

def extract_article_parts(article_text):
    """Extracts article parts from formatted text."""
    result = {
        'title': 'N/A',
        'content': 'N/A',
        'category': 'N/A',
        'date': 'N/A',
        'subtitle': 'N/A',
        'author': 'N/A',
        'url': 'N/A',
        'raw_text': article_text
    }
    
    # Extract header info
    title_match = re.search(r'NASLOV: (.+)', article_text)
    if title_match:
        result['title'] = title_match.group(1).strip()
    
    subtitle_match = re.search(r'PODNASLOV: (.+)', article_text)
    if subtitle_match:
        result['subtitle'] = subtitle_match.group(1).strip()
    
    category_match = re.search(r'RUBRIKA: (.+)', article_text)
    if category_match:
        result['category'] = category_match.group(1).strip()
    
    date_match = re.search(r'DATUM: (.+)', article_text)
    if date_match:
        result['date'] = date_match.group(1).strip()
    
    author_match = re.search(r'AUTOR\(I\): (.+)', article_text)
    if author_match:
        result['author'] = author_match.group(1).strip()
    
    url_match = re.search(r'STRANA: (.+)', article_text)
    if url_match:
        result['url'] = url_match.group(1).strip()
    
    # Extract content (text after header)
    content_match = re.search(r'AUTOR\(I\): .+\n\n(.+)', article_text, re.DOTALL)
    if content_match:
        result['content'] = content_match.group(1).strip()
    
    return result

def filter_articles_in_file(input_file, output_local, output_foreign):
    """
    Filters articles in a single file, separating local and foreign language content.
    Returns (local_count, foreign_count)
    """
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return 0, 0
    
    local_count = 0
    foreign_count = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into individual articles
        articles = content.split("<***>")
        
        # Filter out empty entries
        articles = [a for a in articles if a.strip()]
        
        logger.info(f"Found {len(articles)} articles in file: {input_file}")
        
        local_articles = []
        foreign_articles = []
        
        # Process each article
        for i, article in enumerate(articles):
            # Add back the marker that was removed during splitting
            article = "<***>" + article if not article.startswith("<***>") else article
            
            # Extract parts
            parts = extract_article_parts(article)
            
            # Check language
            if is_foreign_language(parts['title'], parts['content']):
                foreign_count += 1
                foreign_articles.append(article)
                logger.info(f"[{i+1}/{len(articles)}] Foreign article detected: {parts['title']}")
            else:
                local_count += 1
                local_articles.append(article)
                logger.debug(f"[{i+1}/{len(articles)}] Local article: {parts['title']}")
        
        # Write filtered articles
        if local_articles:
            os.makedirs(os.path.dirname(output_local), exist_ok=True)
            with open(output_local, 'w', encoding='utf-8') as f:
                f.write('\n'.join(local_articles))
        
        if foreign_articles:
            os.makedirs(os.path.dirname(output_foreign), exist_ok=True)
            with open(output_foreign, 'w', encoding='utf-8') as f:
                f.write('\n'.join(foreign_articles))
        
        logger.info(f"Filtered {len(articles)} articles: {local_count} local, {foreign_count} foreign")
        return local_count, foreign_count
    
    except Exception as e:
        logger.error(f"Error processing file {input_file}: {str(e)}")
        return 0, 0

def filter_batch_directory(input_dir, output_local_dir, output_foreign_dir):
    """
    Filters all articles in batch files in a directory.
    """
    if not os.path.exists(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return 0, 0
    
    # Create output directories
    os.makedirs(output_local_dir, exist_ok=True)
    os.makedirs(output_foreign_dir, exist_ok=True)
    
    # Find all batch files
    batch_files = [f for f in os.listdir(input_dir) 
                  if f.startswith("PoskokClanci_batch_") and f.endswith(".txt")]
    
    if not batch_files:
        logger.warning(f"No batch files found in {input_dir}")
        return 0, 0
    
    logger.info(f"Found {len(batch_files)} batch files to filter")
    
    # Process each batch file
    total_local = 0
    total_foreign = 0
    
    for i, batch_file in enumerate(sorted(batch_files)):
        input_file = os.path.join(input_dir, batch_file)
        output_local = os.path.join(output_local_dir, batch_file)
        output_foreign = os.path.join(output_foreign_dir, batch_file)
        
        logger.info(f"[{i+1}/{len(batch_files)}] Processing batch file: {batch_file}")
        local_count, foreign_count = filter_articles_in_file(input_file, output_local, output_foreign)
        
        total_local += local_count
        total_foreign += foreign_count
    
    logger.info(f"Filtering complete: {total_local} local articles, {total_foreign} foreign articles")
    return total_local, total_foreign

def filter_all_batches(input_base_dir, output_local_base, output_foreign_base):
    """
    Filters all articles in all batch directories.
    """
    if not os.path.exists(input_base_dir):
        logger.error(f"Input base directory not found: {input_base_dir}")
        return
    
    # Find all batch directories
    batch_dirs = [d for d in os.listdir(input_base_dir) 
                 if os.path.isdir(os.path.join(input_base_dir, d)) and d.startswith("articles_batch_")]
    
    if not batch_dirs:
        logger.warning(f"No batch directories found in {input_base_dir}")
        return
    
    logger.info(f"Found {len(batch_dirs)} batch directories to filter")
    
    # Process each batch directory
    total_local = 0
    total_foreign = 0
    
    for i, batch_dir in enumerate(sorted(batch_dirs)):
        input_dir = os.path.join(input_base_dir, batch_dir)
        output_local_dir = os.path.join(output_local_base, batch_dir)
        output_foreign_dir = os.path.join(output_foreign_base, batch_dir)
        
        logger.info(f"[{i+1}/{len(batch_dirs)}] Processing batch directory: {batch_dir}")
        local_count, foreign_count = filter_batch_directory(input_dir, output_local_dir, output_foreign_dir)
        
        total_local += local_count
        total_foreign += foreign_count
    
    logger.info(f"All batches filtered: {total_local} local articles, {total_foreign} foreign articles")
    
    # Save summary
    summary = {
        "total_processed": total_local + total_foreign,
        "local_articles": total_local,
        "foreign_articles": total_foreign,
        "batch_dirs_processed": len(batch_dirs)
    }
    
    with open(os.path.join(output_local_base, "filter_summary.json"), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Filter summary saved to {os.path.join(output_local_base, 'filter_summary.json')}")

def filter_single_article(article_text):
    """
    Filters a single article text, returning True if it's in local language, False if foreign.
    """
    parts = extract_article_parts(article_text)
    return not is_foreign_language(parts['title'], parts['content'])

def clean_text_and_remove_duplicates(input_files, output_file):
    """
    Combines multiple text files, cleans text, and removes duplicate articles.
    """
    all_articles = []
    article_urls = set()  # Track URLs to avoid duplicates
    
    # Read all input files
    for input_file in input_files:
        if not os.path.exists(input_file):
            logger.warning(f"Input file not found: {input_file}")
            continue
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into articles
            articles = content.split("<***>")
            articles = [a for a in articles if a.strip()]
            
            logger.info(f"Found {len(articles)} articles in {input_file}")
            
            # Process each article
            for article in articles:
                # Add back the marker
                article = "<***>" + article if not article.startswith("<***>") else article
                
                # Extract URL for deduplication
                url_match = re.search(r'STRANA: (.+)', article)
                if url_match:
                    url = url_match.group(1).strip()
                    
                    # Skip if we've seen this URL before
                    if url in article_urls:
                        continue
                    
                    article_urls.add(url)
                
                # Clean up article text
                # 1. Remove excessive newlines
                article = re.sub(r'\n{3,}', '\n\n', article)
                
                # 2. Fix spacing around punctuation
                article = re.sub(r'\s+([.,;:!?])', r'\1', article)
                
                # Add to collection
                all_articles.append(article)
        
        except Exception as e:
            logger.error(f"Error processing file {input_file}: {str(e)}")
    
    # Write combined output
    if all_articles:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_articles))
        
        logger.info(f"Saved {len(all_articles)} unique articles to {output_file}")
        logger.info(f"Removed {len(article_urls) - len(all_articles)} duplicate articles")
    else:
        logger.warning("No articles to save")

def main():
    parser = argparse.ArgumentParser(description='Content Filter for Poskok Scraper')
    parser.add_argument('--input', type=str, required=True,
                        help='Input file or directory to filter')
    parser.add_argument('--output-local', type=str, default='PoskokData/filtered/local',
                        help='Output directory for local language articles')
    parser.add_argument('--output-foreign', type=str, default='PoskokData/filtered/foreign',
                        help='Output directory for foreign language articles')
    parser.add_argument('--mode', choices=['file', 'directory', 'all-batches'],
                        default='file', help='Processing mode')
    parser.add_argument('--combine', action='store_true',
                        help='Combine filtered local articles into a single file')
    parser.add_argument('--combined-output', type=str, default='PoskokData/SviClanci.txt',
                        help='Output file for combined articles')
    args = parser.parse_args()
    
    # Create output directories
    os.makedirs(args.output_local, exist_ok=True)
    os.makedirs(args.output_foreign, exist_ok=True)
    
    # Process based on mode
    if args.mode == 'file':
        logger.info(f"Filtering single file: {args.input}")
        output_local = os.path.join(args.output_local, os.path.basename(args.input))
        output_foreign = os.path.join(args.output_foreign, os.path.basename(args.input))
        local_count, foreign_count = filter_articles_in_file(args.input, output_local, output_foreign)
        logger.info(f"Filtering complete: {local_count} local articles, {foreign_count} foreign articles")
    
    elif args.mode == 'directory':
        logger.info(f"Filtering directory: {args.input}")
        local_count, foreign_count = filter_batch_directory(args.input, args.output_local, args.output_foreign)
        logger.info(f"Filtering complete: {local_count} local articles, {foreign_count} foreign articles")
    
    elif args.mode == 'all-batches':
        logger.info(f"Filtering all batch directories in: {args.input}")
        filter_all_batches(args.input, args.output_local, args.output_foreign)
    
    # Combine filtered articles if requested
    if args.combine:
        logger.info("Combining filtered local articles into a single file")
        
        # Find all filtered local files
        if os.path.isdir(args.output_local):
            local_files = []
            for root, _, files in os.walk(args.output_local):
                for file in files:
                    if file.endswith('.txt'):
                        local_files.append(os.path.join(root, file))
            
            if local_files:
                logger.info(f"Found {len(local_files)} local article files to combine")
                clean_text_and_remove_duplicates(local_files, args.combined_output)
            else:
                logger.warning(f"No local article files found in {args.output_local}")
        else:
            logger.error(f"Local output is not a directory: {args.output_local}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combiner for Poskok Scraper
--------------------------
Combines multiple batch files into a single output file.
Handles deduplication and creation of archive for download.
"""

import os
import re
import shutil
import json
import logging
import argparse
import zipfile
from pathlib import Path
from datetime import datetime

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

def find_batch_files(input_dir, recursive=True):
    """Finds all batch files in the input directory."""
    batch_files = []
    
    if recursive:
        # Walk through all subdirectories
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.startswith("PoskokClanci_batch_") and file.endswith(".txt"):
                    batch_files.append(os.path.join(root, file))
    else:
        # Only look in the top directory
        for file in os.listdir(input_dir):
            if file.startswith("PoskokClanci_batch_") and file.endswith(".txt"):
                batch_files.append(os.path.join(input_dir, file))
    
    # Sort batch files naturally
    batch_files.sort(key=lambda x: int(re.search(r'batch_(\d+)', x).group(1)) 
                    if re.search(r'batch_(\d+)', x) else 0)
    
    logger.info(f"Found {len(batch_files)} batch files")
    return batch_files

def extract_article_urls(article_text):
    """Extracts URL from an article text."""
    url_match = re.search(r'STRANA: (.+)', article_text)
    if url_match:
        return url_match.group(1).strip()
    return None

def combine_batch_files(batch_files, output_file, deduplicate=True):
    """Combines multiple batch files into a single output file with deduplication."""
    if not batch_files:
        logger.warning("No batch files to combine")
        return 0
    
    all_articles = []
    article_urls = set()  # For deduplication
    total_articles = 0
    duplicate_count = 0
    
    # Process each batch file
    for i, batch_file in enumerate(batch_files):
        logger.info(f"[{i+1}/{len(batch_files)}] Processing: {batch_file}")
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into individual articles
            articles = content.split("<***>")
            articles = [a for a in articles if a.strip()]
            
            batch_articles = 0
            batch_duplicates = 0
            
            # Process each article
            for article in articles:
                total_articles += 1
                
                # Add back the marker
                article = "<***>" + article if not article.startswith("<***>") else article
                
                if deduplicate:
                    # Extract URL for deduplication
                    url = extract_article_urls(article)
                    
                    if url:
                        # Skip if we've seen this URL before
                        if url in article_urls:
                            duplicate_count += 1
                            batch_duplicates += 1
                            continue
                        
                        article_urls.add(url)
                
                # Add to the list of articles to save
                all_articles.append(article)
                batch_articles += 1
            
            logger.info(f"Batch {i+1}: {batch_articles} articles added, {batch_duplicates} duplicates skipped")
        
        except Exception as e:
            logger.error(f"Error processing {batch_file}: {str(e)}")
    
    # Write combined output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_articles))
    
    logger.info(f"Combination complete: {len(all_articles)} articles saved to {output_file}")
    if deduplicate:
        logger.info(f"Removed {duplicate_count} duplicate articles from {total_articles} total")
    
    return len(all_articles)

def create_zip_archive(input_dir, output_zip=None):
    """Creates a ZIP archive of the specified directory."""
    if not os.path.exists(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return None
    
    # Default zip filename uses directory name and timestamp
    if output_zip is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = os.path.basename(input_dir)
        output_zip = f"{dir_name}_{timestamp}.zip"
    
    # Create zip file
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through directory and add all files
            for root, _, files in os.walk(input_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate path relative to input_dir for archive structure
                    rel_path = os.path.relpath(file_path, input_dir)
                    zipf.write(file_path, rel_path)
        
        logger.info(f"Created ZIP archive: {output_zip}")
        return output_zip
    
    except Exception as e:
        logger.error(f"Error creating ZIP archive: {str(e)}")
        return None

def create_summary(input_files, output_file, article_count, duplicate_count=0):
    """Creates a summary of the combined data."""
    if not output_file:
        return
    
    # Generate summary information
    summary = {
        "timestamp": datetime.now().isoformat(),
        "input_files": len(input_files),
        "total_articles": article_count + duplicate_count,
        "unique_articles": article_count,
        "duplicate_articles": duplicate_count,
        "output_file": output_file
    }
    
    # Write summary to file
    summary_file = os.path.splitext(output_file)[0] + "_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Summary saved to {summary_file}")
    return summary_file

def generate_report(summary, output_file):
    """Generates a human-readable report from summary data."""
    if not summary or not output_file:
        return
    
    # Create report text
    report = f"""
=== POSKOK SCRAPER REPORT ===
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

SUMMARY:
- Total input files processed: {summary['input_files']}
- Total articles found: {summary['total_articles']}
- Unique articles saved: {summary['unique_articles']}
- Duplicate articles removed: {summary['duplicate_articles']}

OUTPUT:
- Combined articles saved to: {summary['output_file']}

COMPLETION RATE:
- Articles successfully processed: {summary['unique_articles']} / {summary['total_articles']}
- Success rate: {(summary['unique_articles'] / summary['total_articles'] * 100) if summary['total_articles'] > 0 else 0:.2f}%

This report was generated automatically by Poskok Scraper.
"""
    
    # Write report to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Report saved to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Combiner for Poskok Scraper')
    parser.add_argument('--input-dir', type=str, default='PoskokData/filtered/local',
                        help='Input directory containing batch files')
    parser.add_argument('--output-file', type=str, default='PoskokData/SviClanci.txt',
                        help='Output file for combined articles')
    parser.add_argument('--no-deduplicate', action='store_true',
                        help='Skip deduplication of articles')
    parser.add_argument('--create-zip', action='store_true',
                        help='Create a ZIP archive of the output')
    parser.add_argument('--zip-file', type=str, default=None,
                        help='Output ZIP file name (default: auto-generated)')
    parser.add_argument('--non-recursive', action='store_true',
                        help='Do not search subdirectories for batch files')
    parser.add_argument('--generate-report', action='store_true',
                        help='Generate a human-readable report')
    args = parser.parse_args()
    
    # Find batch files
    batch_files = find_batch_files(args.input_dir, not args.non_recursive)
    
    if not batch_files:
        logger.error(f"No batch files found in {args.input_dir}")
        return
    
    # Combine files
    deduplicate = not args.no_deduplicate
    article_count = combine_batch_files(batch_files, args.output_file, deduplicate)
    
    # Create summary
    total_articles = sum(1 for batch_file in batch_files 
                        for _ in open(batch_file, 'r', encoding='utf-8').read().split("<***>") 
                        if _.strip())
    duplicate_count = total_articles - article_count if deduplicate else 0
    
    summary = create_summary(
        batch_files, 
        args.output_file, 
        article_count,
        duplicate_count
    )
    
    # Generate report if requested
    if args.generate_report:
        report_file = os.path.splitext(args.output_file)[0] + "_report.txt"
        generate_report(summary, report_file)
    
    # Create ZIP archive if requested
    if args.create_zip:
        # Create a directory with all relevant files
        output_dir = os.path.dirname(args.output_file)
        archive_dir = os.path.join(output_dir, "PoskokArchive")
        os.makedirs(archive_dir, exist_ok=True)
        
        # Copy files to archive directory
        shutil.copy2(args.output_file, archive_dir)
        
        # Copy summary and report if they exist
        summary_file = os.path.splitext(args.output_file)[0] + "_summary.json"
        if os.path.exists(summary_file):
            shutil.copy2(summary_file, archive_dir)
        
        report_file = os.path.splitext(args.output_file)[0] + "_report.txt"
        if os.path.exists(report_file):
            shutil.copy2(report_file, archive_dir)
        
        # Create ZIP archive
        create_zip_archive(archive_dir, args.zip_file)

if __name__ == "__main__":
    main()
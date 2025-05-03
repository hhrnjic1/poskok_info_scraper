#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point for Poskok Scraper
----------------------------------
Orchestrates the entire scraping process by coordinating all components.
Provides a simple CLI interface to run complete or partial scraping process.
"""

import os
import sys
import json
import logging
import argparse
import time
import subprocess
import shutil
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("poskok_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_file='scraping_config.json'):
    """Loads configuration from file or creates default."""
    default_config = {
        "start_year": 2012,
        "end_year": datetime.now().year,
        "max_pages_per_category": 300,
        "batch_size": 100,
        "checkpoint_interval": 20,
        "max_retries": 5,
        "retry_delay": 5,
        "timeout": 45,
        "scrape_archive": True,
        "force_refresh_links": False,
        "output_folder": "PoskokData",
        "max_workers": None,
        "batch_link_size": 1000
    }
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"Configuration loaded from {config_file}")
            
            # Fill in with defaults for any missing keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("Creating default configuration")
        config = default_config
        
        # Save default config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    # Print active configuration
    logger.info("Active configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    return config

def setup_directories(config):
    """Creates all necessary directories for the scraper."""
    base_dir = config['output_folder']
    
    directories = {
        'base': base_dir,
        'links': os.path.join(base_dir, 'links'),
        'link_batches': os.path.join(base_dir, 'link_batches'),
        'articles': os.path.join(base_dir, 'articles'),
        'filtered': {
            'base': os.path.join(base_dir, 'filtered'),
            'local': os.path.join(base_dir, 'filtered', 'local'),
            'foreign': os.path.join(base_dir, 'filtered', 'foreign')
        },
        'final': os.path.join(base_dir, 'final')
    }
    
    # Create all directories
    for name, path in directories.items():
        if isinstance(path, dict):
            for subname, subpath in path.items():
                os.makedirs(subpath, exist_ok=True)
                logger.debug(f"Created directory: {subpath}")
        else:
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Created directory: {path}")
    
    return directories

def run_command(command, description=None):
    """Runs a command and logs the output."""
    if description:
        logger.info(f"Starting: {description}")
    
    logger.info(f"Command: {' '.join(command)}")
    
    try:
        # Run the process and capture output
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"Command completed successfully")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False, e.stderr

def collect_links(config, dirs):
    """Runs the link collector to gather article URLs."""
    logger.info("=== Starting Link Collection Phase ===")
    
    command = [
        sys.executable, "link_collector.py",
        "--output-dir", dirs['links'],
        "--config", "scraping_config.json"
    ]
    
    if config['force_refresh_links']:
        command.append("--force-refresh")
    
    success, output = run_command(command, "Link collection")
    
    if not success:
        logger.error("Link collection failed")
        return False
    
    # Check if links were collected
    link_file = os.path.join(dirs['links'], "all_links.json")
    if not os.path.exists(link_file):
        logger.error(f"Link file not found: {link_file}")
        return False
    
    try:
        with open(link_file, 'r', encoding='utf-8') as f:
            links = json.load(f)
            logger.info(f"Collected {len(links)} links")
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"Error reading link file: {link_file}")
        return False
    
    return True

def process_links(config, dirs):
    """Processes collected links to scrape articles."""
    logger.info("=== Starting Article Scraping Phase ===")
    
    # Use batch_processor.py to manage article scraping in parallel
    command = [
        sys.executable, "batch_processor.py",
        "--input-dir", dirs['link_batches'],
        "--output-dir", dirs['articles'],
        "--config", "scraping_config.json"
    ]
    
    if config['max_workers']:
        command.extend(["--workers", str(config['max_workers'])])
    
    success, output = run_command(command, "Article scraping")
    
    if not success:
        logger.error("Article scraping failed")
        return False
    
    return True

def filter_articles(config, dirs):
    """Filters articles to separate local and foreign language content."""
    logger.info("=== Starting Article Filtering Phase ===")
    
    command = [
        sys.executable, "filter.py",
        "--input", dirs['articles'],
        "--output-local", dirs['filtered']['local'],
        "--output-foreign", dirs['filtered']['foreign'],
        "--mode", "all-batches"
    ]
    
    success, output = run_command(command, "Article filtering")
    
    if not success:
        logger.error("Article filtering failed")
        return False
    
    return True

def combine_articles(config, dirs):
    """Combines filtered articles into a single output file."""
    logger.info("=== Starting Article Combination Phase ===")
    
    output_file = os.path.join(dirs['final'], "SviClanci.txt")
    
    command = [
        sys.executable, "combine.py",
        "--input-dir", dirs['filtered']['local'],
        "--output-file", output_file,
        "--create-zip",
        "--generate-report"
    ]
    
    success, output = run_command(command, "Article combination")
    
    if not success:
        logger.error("Article combination failed")
        return False
    
    return True

def create_archive(config, dirs):
    """Creates a final ZIP archive for download."""
    logger.info("=== Creating Final Archive ===")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_file = f"PoskokArchive_{timestamp}.zip"
    
    command = [
        sys.executable, "combine.py",
        "--input-dir", dirs['filtered']['local'],
        "--output-file", os.path.join(dirs['final'], "SviClanci.txt"),
        "--create-zip",
        "--zip-file", zip_file,
        "--generate-report"
    ]
    
    success, output = run_command(command, "Archive creation")
    
    if not success:
        logger.error("Archive creation failed")
        return False
    
    if os.path.exists(zip_file):
        logger.info(f"Archive created: {zip_file}")
        
        # Copy archive to final directory
        shutil.copy2(zip_file, os.path.join(dirs['final'], zip_file))
    
    return True

def full_scraping_pipeline(config, dirs):
    """Runs the complete scraping pipeline from start to finish."""
    logger.info("Starting full scraping pipeline")
    
    # Record start time
    start_time = time.time()
    
    # Step 1: Collect links
    if not collect_links(config, dirs):
        logger.error("Link collection failed. Aborting pipeline.")
        return False
    
    # Step 2: Process links to scrape articles
    if not process_links(config, dirs):
        logger.error("Article scraping failed. Aborting pipeline.")
        return False
    
    # Step 3: Filter articles
    if not filter_articles(config, dirs):
        logger.error("Article filtering failed. Aborting pipeline.")
        return False
    
    # Step 4: Combine articles
    if not combine_articles(config, dirs):
        logger.error("Article combination failed. Aborting pipeline.")
        return False
    
    # Step 5: Create final archive
    if not create_archive(config, dirs):
        logger.error("Archive creation failed.")
        # Continue anyway since this is the last step
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info(f"Full scraping pipeline completed in {int(hours)}h {int(minutes)}m {int(seconds)}s")
    return True

def main():
    parser = argparse.ArgumentParser(description='Poskok Scraper - Main Entry Point')
    
    # Main operation modes
    parser.add_argument('--config', type=str, default='scraping_config.json',
                        help='Configuration file path')
    parser.add_argument('--full-pipeline', action='store_true',
                        help='Run the full scraping pipeline')
    
    # Individual component modes
    parser.add_argument('--collect-links', action='store_true',
                        help='Only collect links from the portal')
    parser.add_argument('--process-links', action='store_true',
                        help='Only process collected links to scrape articles')
    parser.add_argument('--filter-articles', action='store_true',
                        help='Only filter already scraped articles')
    parser.add_argument('--combine-articles', action='store_true',
                        help='Only combine filtered articles into a single file')
    parser.add_argument('--create-archive', action='store_true',
                        help='Only create a final ZIP archive for download')
    
    # Force options
    parser.add_argument('--force-refresh-links', action='store_true',
                        help='Force refresh of links even if they already exist')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Apply command line overrides
    if args.force_refresh_links:
        config['force_refresh_links'] = True
    
    # Setup directories
    dirs = setup_directories(config)
    
    # Determine which operations to run
    if args.full_pipeline:
        full_scraping_pipeline(config, dirs)
    else:
        # Run individual components as requested
        if args.collect_links:
            collect_links(config, dirs)
        
        if args.process_links:
            process_links(config, dirs)
        
        if args.filter_articles:
            filter_articles(config, dirs)
        
        if args.combine_articles:
            combine_articles(config, dirs)
        
        if args.create_archive:
            create_archive(config, dirs)
        
        # If no specific operation was requested, show help
        if not any([args.collect_links, args.process_links, args.filter_articles, 
                   args.combine_articles, args.create_archive]):
            parser.print_help()

if __name__ == "__main__":
    logger.info("=== Poskok Scraper Started ===")
    try:
        main()
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
    finally:
        logger.info("=== Poskok Scraper Finished ===")
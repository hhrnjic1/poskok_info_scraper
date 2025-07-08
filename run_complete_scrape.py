#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Site Scraper Runner with Fixed Paths
-------------------------------------------
Orchestrates the complete scraping of Poskok.info
"""

import os
import sys
import json
import logging
import time
import shutil
from datetime import datetime
import subprocess
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)  # Change to script directory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("complete_scrape.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create all necessary directories."""
    directories = [
        'PoskokCompleteArchive',
        'PoskokCompleteArchive/links',
        'PoskokCompleteArchive/articles',
        'PoskokCompleteArchive/filtered',
        'PoskokCompleteArchive/final',
        'PoskokCompleteArchive/logs',
        'PoskokCompleteArchive/checkpoints',
        'PoskokCompleteArchive/raw_html',
        'PoskokCompleteArchive/metadata'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    logger.info("Directories created successfully")

def check_required_files():
    """Check if all required files exist."""
    required_files = [
        'enhanced_link_collector.py',
        'enhanced_article_scraper.py',
        'complete_scrape_config.json',
        'batch_processor.py',
        'filter.py',
        'combine.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        logger.error(f"Current directory: {os.getcwd()}")
        logger.error("Please ensure all required files are in the same directory as this script.")
        return False
    
    logger.info("All required files found")
    return True

def run_command(command, description):
    """Run a command and log output."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {' '.join(command)}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Stream output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
        
        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(stdout.strip())
        if stderr:
            logger.error(f"STDERR: {stderr.strip()}")
        
        # Get return code
        rc = process.poll()
        
        if rc == 0:
            logger.info(f"Successfully completed: {description}")
            return True
        else:
            logger.error(f"Failed: {description} (return code: {rc})")
            return False
            
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        logger.exception("Full traceback:")
        return False

def run_complete_scrape():
    """Run the complete scraping process."""
    start_time = time.time()
    
    logger.info("=== Starting Complete Poskok.info Scrape ===")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Check for required files
    if not check_required_files():
        return False
    
    # 1. Setup directories
    setup_directories()
    
    # 2. Run enhanced link collector
    logger.info("Phase 1: Collecting all links from the site...")
    link_collector_cmd = [
        sys.executable,
        "enhanced_link_collector.py",
        "--config", "complete_scrape_config.json",
        "--output", "PoskokCompleteArchive/links/all_links.json",
        "--max-depth", "15"
    ]
    
    if not run_command(link_collector_cmd, "Enhanced link collection"):
        logger.error("Link collection failed. Aborting.")
        return False
    
    # 3. Analyze collected links
    try:
        with open("PoskokCompleteArchive/links/all_links.json", "r") as f:
            link_data = json.load(f)
            total_links = len(link_data.get('links', []))
            logger.info(f"Total links collected: {total_links}")
    except Exception as e:
        logger.error(f"Error reading links file: {str(e)}")
        return False
    
    # 4. Create batches for processing
    logger.info("Creating link batches...")
    create_batches_cmd = [
        sys.executable,
        "-c",
        """
import json
import os

with open('PoskokCompleteArchive/links/all_links.json', 'r') as f:
    data = json.load(f)
    links = data.get('links', [])

batch_size = 1000
batch_dir = 'PoskokCompleteArchive/link_batches'
os.makedirs(batch_dir, exist_ok=True)

for i in range(0, len(links), batch_size):
    batch = links[i:i+batch_size]
    batch_file = os.path.join(batch_dir, f'batch_{i//batch_size+1}.json')
    with open(batch_file, 'w') as bf:
        json.dump(batch, bf)

print(f"Created {(len(links) + batch_size - 1) // batch_size} batches")
"""
    ]
    
    run_command(create_batches_cmd, "Batch creation")
    
    # 5. Run enhanced article scraper
    logger.info("Phase 2: Scraping all articles...")
    scraper_cmd = [
        sys.executable,
        "batch_processor.py",
        "--input-dir", "PoskokCompleteArchive/link_batches",
        "--output-dir", "PoskokCompleteArchive/articles",
        "--config", "complete_scrape_config.json",
        "--workers", "8"
    ]
    
    if not run_command(scraper_cmd, "Article scraping"):
        logger.warning("Some articles may have failed to scrape. Continuing...")
    
    # 6. Filter articles (with less aggressive filtering)
    logger.info("Phase 3: Filtering articles...")
    filter_cmd = [
        sys.executable,
        "filter.py",
        "--input", "PoskokCompleteArchive/articles",
        "--output-local", "PoskokCompleteArchive/filtered/local",
        "--output-foreign", "PoskokCompleteArchive/filtered/foreign",
        "--mode", "all-batches"
    ]
    
    if not run_command(filter_cmd, "Article filtering"):
        logger.warning("Filtering encountered issues. Continuing...")
    
    # 7. Combine all articles
    logger.info("Phase 4: Combining all articles...")
    combine_cmd = [
        sys.executable,
        "combine.py",
        "--input-dir", "PoskokCompleteArchive/filtered/local",
        "--output-file", "PoskokCompleteArchive/final/AllPoskokArticles_Complete.txt",
        "--create-zip",
        "--generate-report"
    ]
    
    if not run_command(combine_cmd, "Article combination"):
        logger.warning("Combination encountered issues.")
    
    # 8. Generate final statistics
    end_time = time.time()
    duration = end_time - start_time
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info("=== Complete Scraping Process Finished ===")
    logger.info(f"Total time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    
    # Count articles
    try:
        with open("PoskokCompleteArchive/final/AllPoskokArticles_Complete.txt", "r") as f:
            content = f.read()
            article_count = content.count("<***>")
            logger.info(f"Total articles scraped: {article_count}")
    except:
        pass
    
    # Create summary report
    summary = {
        "start_time": datetime.fromtimestamp(start_time).isoformat(),
        "end_time": datetime.fromtimestamp(end_time).isoformat(),
        "duration_seconds": duration,
        "total_links_found": total_links,
        "articles_scraped": article_count if 'article_count' in locals() else "Unknown",
        "status": "Complete"
    }
    
    with open("PoskokCompleteArchive/final/scrape_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info("Summary report created: PoskokCompleteArchive/final/scrape_summary.json")
    
    return True

if __name__ == "__main__":
    try:
        success = run_complete_scrape()
        if success:
            logger.info("Complete scraping process finished successfully!")
        else:
            logger.error("Scraping process encountered errors.")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {str(e)}")
        sys.exit(1)
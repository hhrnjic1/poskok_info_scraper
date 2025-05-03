#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Processor for Poskok Scraper
---------------------------------
Manages parallel processing of article batches.
Distributes work across multiple processes for faster scraping.
"""

import os
import json
import logging
import argparse
import time
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys

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

# Import from config file
from config import DEFAULT_CONFIG

def get_batch_files(batch_dir="link_batches"):
    """Get all link batch files in the specified directory."""
    if not os.path.exists(batch_dir):
        logger.error(f"Batch directory not found: {batch_dir}")
        return []

    # Check for batch index file first
    index_file = os.path.join(batch_dir, "batch_index.json")
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
                return index.get('batches', [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading batch index: {str(e)}")

    # Fall back to directory listing if index file doesn't exist or is invalid
    return [os.path.join(batch_dir, f) for f in os.listdir(batch_dir)
            if f.startswith('links_batch_') and f.endswith('.json')]

def run_article_scraper(batch_file, output_dir, config=None):
    """Run article scraper on a specific batch file."""
    if not os.path.exists(batch_file):
        logger.error(f"Batch file not found: {batch_file}")
        return False

    # Prepare command to run article scraper
    cmd = [sys.executable, "article_scraper.py", "--batch", batch_file, "--output", output_dir]
    
    # Add config file if specified
    if config:
        cmd.extend(["--config", config])
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        # Run the process and capture output
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Batch processing completed: {batch_file}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing batch {batch_file}: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def process_batch_worker(args):
    """Worker function for multiprocessing pool."""
    batch_file, output_dir, config, batch_num, total_batches = args
    process_name = multiprocessing.current_process().name
    logger.info(f"[{process_name}] Starting batch {batch_num}/{total_batches}: {batch_file}")
    success = run_article_scraper(batch_file, output_dir, config)
    return batch_file, success

def process_batches_parallel(batch_files, output_dir, config_file=None, max_workers=None):
    """Process multiple batch files in parallel."""
    if not batch_files:
        logger.error("No batch files to process")
        return

    # Determine number of workers (default to CPU count)
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(batch_files))
    
    logger.info(f"Processing {len(batch_files)} batches with {max_workers} workers")
    
    # Prepare arguments for each batch
    args_list = [
        (batch_file, output_dir, config_file, i+1, len(batch_files)) 
        for i, batch_file in enumerate(batch_files)
    ]
    
    # Create a pool of workers
    with multiprocessing.Pool(processes=max_workers) as pool:
        # Start processing batches
        results = pool.map(process_batch_worker, args_list)
    
    # Count successes
    successes = sum(1 for _, success in results if success)
    logger.info(f"Batch processing complete: {successes}/{len(batch_files)} batches successfully processed")
    
    # Return list of failed batches
    failed_batches = [batch for batch, success in results if not success]
    return failed_batches

def check_batch_status(output_dir):
    """Check the status of batch processing by analyzing output directories."""
    if not os.path.exists(output_dir):
        logger.error(f"Output directory not found: {output_dir}")
        return
    
    # Find all batch output directories
    batch_dirs = [d for d in os.listdir(output_dir) 
                 if os.path.isdir(os.path.join(output_dir, d)) and d.startswith("articles_batch_")]
    
    if not batch_dirs:
        logger.info("No batch output directories found")
        return
    
    logger.info(f"Found {len(batch_dirs)} batch output directories")
    
    # Check each batch directory
    for batch_dir in sorted(batch_dirs):
        full_path = os.path.join(output_dir, batch_dir)
        
        # Count batch files
        batch_files = [f for f in os.listdir(full_path) 
                      if f.startswith("PoskokClanci_batch_") and f.endswith(".txt")]
        
        # Check progress file
        progress_file = os.path.join(full_path, "progress.json")
        processed_count = 0
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    processed_urls = json.load(f)
                    processed_count = len(processed_urls)
            except:
                pass
        
        logger.info(f"Batch {batch_dir}: {len(batch_files)} output files, {processed_count} URLs processed")

def retry_failed_batches(failed_batches, output_dir, config_file=None):
    """Retry processing of failed batches."""
    if not failed_batches:
        logger.info("No failed batches to retry")
        return
    
    logger.info(f"Retrying {len(failed_batches)} failed batches...")
    
    # Process each failed batch sequentially
    for i, batch_file in enumerate(failed_batches):
        logger.info(f"Retrying batch {i+1}/{len(failed_batches)}: {batch_file}")
        success = run_article_scraper(batch_file, output_dir, config_file)
        if success:
            logger.info(f"Successfully reprocessed batch: {batch_file}")
        else:
            logger.error(f"Failed to reprocess batch: {batch_file}")

def main():
    parser = argparse.ArgumentParser(description='Batch processor for Poskok Scraper')
    parser.add_argument('--input-dir', type=str, default='link_batches',
                        help='Directory containing link batch files')
    parser.add_argument('--output-dir', type=str, default='PoskokData/articles',
                        help='Output directory for article batches')
    parser.add_argument('--config', type=str, default='scraping_config.json',
                        help='Configuration file path')
    parser.add_argument('--workers', type=int, default=None,
                        help='Number of parallel workers (default: CPU count)')
    parser.add_argument('--status', action='store_true',
                        help='Check status of batch processing')
    parser.add_argument('--batch-range', type=str,
                        help='Process only a range of batches (e.g., "1-5" or "7,9,12")')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # If status check requested, do that and exit
    if args.status:
        check_batch_status(args.output_dir)
        return
    
    # Get all batch files
    batch_files = get_batch_files(args.input_dir)
    
    if not batch_files:
        logger.error(f"No batch files found in {args.input_dir}")
        return
    
    logger.info(f"Found {len(batch_files)} batch files")
    
    # Filter batch files if range specified
    if args.batch_range:
        try:
            selected_batches = []
            
            # Handle ranges like "1-5"
            if '-' in args.batch_range:
                start, end = map(int, args.batch_range.split('-'))
                selected_indices = list(range(start-1, end))
                selected_batches = [batch_files[i] for i in selected_indices if i < len(batch_files)]
            
            # Handle comma-separated list like "7,9,12"
            elif ',' in args.batch_range:
                indices = [int(i)-1 for i in args.batch_range.split(',')]
                selected_batches = [batch_files[i] for i in indices if i < len(batch_files)]
            
            # Handle single number
            else:
                index = int(args.batch_range) - 1
                if index < len(batch_files):
                    selected_batches = [batch_files[index]]
            
            if selected_batches:
                batch_files = selected_batches
                logger.info(f"Selected {len(batch_files)} batches to process based on range: {args.batch_range}")
            else:
                logger.warning(f"No batches match the specified range: {args.batch_range}")
                return
                
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid batch range specification: {args.batch_range}. Error: {str(e)}")
            return
    
    # Process batches in parallel
    start_time = time.time()
    failed_batches = process_batches_parallel(
        batch_files, args.output_dir, args.config, args.workers)
    
    # Retry failed batches
    if failed_batches:
        logger.info(f"{len(failed_batches)} batches failed, retrying...")
        retry_failed_batches(failed_batches, args.output_dir, args.config)
    
    # Report total time
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    logger.info(f"Total processing time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    
    # Final status check
    check_batch_status(args.output_dir)

if __name__ == "__main__":
    main()
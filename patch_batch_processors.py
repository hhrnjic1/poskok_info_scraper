#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch Script for Batch Processor
-------------------------------
Modifies the batch processor to optimize for quick testing.
"""

import os
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def patch_batch_processor():
    """Patch batch_processor.py for quick testing."""
    file_path = "batch_processor.py"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Add quick test config loading
    if "def process_batches_parallel(" in content and "# QUICK TEST MODE" not in content:
        content = content.replace(
            "def process_batches_parallel(batch_files, output_dir, config_file=None, max_workers=None):",
            """def process_batches_parallel(batch_files, output_dir, config_file=None, max_workers=None):
    \"\"\"Process multiple batch files in parallel.\"\"\"
    # QUICK TEST MODE
    quick_test = False
    try:
        if config_file and config_file == "quick_test_config.json":
            with open(config_file, "r") as f:
                quick_config = json.load(f)
                quick_test = quick_config.get("quick_test", False)
                if quick_test:
                    logger.info("RUNNING IN QUICK TEST MODE")
                    # Limit the number of batches for quick test
                    max_batches = quick_config.get("max_links_to_process", 50) // quick_config.get("batch_link_size", 20) + 1
                    if len(batch_files) > max_batches:
                        logger.info(f"QUICK TEST: Limiting batches from {len(batch_files)} to {max_batches}")
                        batch_files = batch_files[:max_batches]
    except (FileNotFoundError, json.JSONDecodeError):
        pass"""
        )
    
    # Write the modified file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"Successfully patched {file_path} for quick testing")
    return True

def patch_combiner():
    """Patch combiner.py for quick testing."""
    file_path = "combine.py"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Add quick test version check in create_zip_archive function
    if "def create_zip_archive(input_dir, output_zip=None):" in content and "# QUICK TEST MODE" not in content:
        content = content.replace(
            "def create_zip_archive(input_dir, output_zip=None):",
            """def create_zip_archive(input_dir, output_zip=None):
    \"\"\"Creates a ZIP archive of the specified directory.\"\"\"
    # QUICK TEST MODE
    quick_test = False
    try:
        with open("quick_test_config.json", "r") as f:
            quick_config = json.load(f)
            quick_test = quick_config.get("quick_test", False)
            if quick_test:
                logger.info("QUICK TEST MODE: Using simplified ZIP archiving")
    except (FileNotFoundError, json.JSONDecodeError):
        pass"""
        )
        
        # Simplify the zip creation for quick test
        content = content.replace(
            "with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:",
            """with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Simplified archiving in quick test mode
            if quick_test:
                # Just add the main output file
                main_file = os.path.join(input_dir, os.path.basename(input_dir) + ".txt")
                if os.path.exists(main_file):
                    zipf.write(main_file, os.path.basename(main_file))
                    logger.info(f"QUICK TEST: Added only main file to archive")
                    return output_zip"""
        )
    
    # Write the modified file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"Successfully patched {file_path} for quick testing")
    return True

def patch_filter():
    """Patch filter.py for quick testing."""
    file_path = "filter.py"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Add quick test check in filter_all_batches function
    if "def filter_all_batches(" in content and "# QUICK TEST MODE" not in content:
        content = content.replace(
            "def filter_all_batches(input_base_dir, output_local_base, output_foreign_base):",
            """def filter_all_batches(input_base_dir, output_local_base, output_foreign_base):
    \"\"\"Filters all articles in all batch directories.\"\"\"
    # QUICK TEST MODE
    quick_test = False
    try:
        with open("quick_test_config.json", "r") as f:
            quick_config = json.load(f)
            quick_test = quick_config.get("quick_test", False)
            if quick_test:
                logger.info("RUNNING IN QUICK TEST MODE: Simplified filtering")
    except (FileNotFoundError, json.JSONDecodeError):
        pass"""
        )
    
    # Write the modified file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"Successfully patched {file_path} for quick testing")
    return True

if __name__ == "__main__":
    patch_batch_processor()
    patch_combiner() 
    patch_filter()
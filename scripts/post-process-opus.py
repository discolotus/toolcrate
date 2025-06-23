#!/usr/bin/env python3
"""Standalone script for post-processing opus files to FLAC."""

import sys
import argparse
import logging
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from toolcrate.wishlist.post_processor import PostProcessor
from toolcrate.config.manager import ConfigManager

def main():
    """Main entry point for opus post-processing."""
    parser = argparse.ArgumentParser(description="Post-process opus files to FLAC")
    parser.add_argument("directory", help="Directory to process")
    parser.add_argument("--index-path", help="Path to sldl index file")
    parser.add_argument("--config", "-c", default="config/toolcrate.yaml",
                       help="Path to configuration file")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be processed without doing it")
    parser.add_argument("--keep-original", action="store_true",
                       help="Keep original opus files after transcoding")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        wishlist_config = config_manager.config.get('wishlist', {})
        
        # Override post-processing settings based on arguments
        post_processing_config = wishlist_config.get('post_processing', {})
        post_processing_config['enabled'] = True
        post_processing_config['transcode_opus_to_flac'] = True
        post_processing_config['update_index'] = True
        
        if args.keep_original:
            post_processing_config['delete_original_opus'] = False
        
        # Initialize post-processor
        post_processor = PostProcessor(post_processing_config)
        
        # Check ffmpeg availability
        if not post_processor.check_ffmpeg_available():
            logger.error("ffmpeg is not available - cannot transcode opus files")
            return 1
        
        directory = Path(args.directory)
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1
        
        index_path = None
        if args.index_path:
            index_path = Path(args.index_path)
            if not index_path.exists():
                logger.warning(f"Index file does not exist: {index_path}")
        
        # Find opus files first
        opus_files = list(directory.rglob("*.opus"))
        if not opus_files:
            logger.info("No opus files found to process")
            return 0
        
        logger.info(f"Found {len(opus_files)} opus files to process:")
        for opus_file in opus_files:
            logger.info(f"  {opus_file.relative_to(directory)}")
        
        if args.dry_run:
            logger.info("Dry run - no files will be processed")
            return 0
        
        # Process the directory
        logger.info("Starting post-processing...")
        results = post_processor.process_directory(directory, index_path)
        
        # Report results
        if results['status'] == 'completed':
            logger.info(f"Post-processing completed successfully")
            logger.info(f"Files processed: {results['processed']}")
            
            if results['transcoded']:
                logger.info(f"Transcoded files:")
                for transcoded in results['transcoded']:
                    original = Path(transcoded['original'])
                    new_file = Path(transcoded['transcoded'])
                    logger.info(f"  {original.name} -> {new_file.name}")
                    if transcoded['deleted_original']:
                        logger.info(f"    (original deleted)")
            
            if results['errors']:
                logger.warning(f"Errors encountered: {len(results['errors'])}")
                for error in results['errors']:
                    logger.warning(f"  {error}")
                return 1
                
        else:
            logger.error(f"Post-processing failed: {results.get('message', 'Unknown error')}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
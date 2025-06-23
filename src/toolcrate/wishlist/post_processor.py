#!/usr/bin/env python3
"""Post-processing module for wishlist downloads."""

import os
import subprocess
import logging
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PostProcessor:
    """Handles post-processing of downloaded files."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the post-processor.
        
        Args:
            config: Post-processing configuration
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        # Support both old and new config keys for backward compatibility
        self.transcode_opus = config.get('transcode_opus', config.get('transcode_opus_to_flac', False))
        self.output_format = config.get('output_format', 'flac').lower()
        self.aac_bitrate = config.get('aac_bitrate', 256)
        self.flac_compression_level = config.get('flac_compression_level', 8)
        self.update_index = config.get('update_index', True)
        self.delete_original = config.get('delete_original_opus', True)
        
        # Validate output format
        if self.output_format not in ['flac', 'aac']:
            logger.warning(f"Invalid output format '{self.output_format}', defaulting to 'flac'")
            self.output_format = 'flac'
        
    def process_directory(self, directory: Path, index_path: Optional[Path] = None) -> Dict[str, Any]:
        """Process all files in a directory.
        
        Args:
            directory: Directory to process
            index_path: Optional specific index file path
            
        Returns:
            Dictionary with processing results
        """
        if not self.enabled:
            logger.debug("Post-processing disabled")
            return {'status': 'disabled', 'processed': 0}
        
        results = {
            'status': 'completed',
            'processed': 0,
            'transcoded': [],
            'errors': [],
            'index_updates': 0
        }
        
        if self.transcode_opus:
            opus_results = self._transcode_opus_files(directory)
            results['processed'] += opus_results['processed']
            results['transcoded'].extend(opus_results['transcoded'])
            results['errors'].extend(opus_results['errors'])
            
            # Update index files if files were transcoded
            if opus_results['transcoded'] and self.update_index:
                if index_path:
                    # Update specific index file
                    updates = self._update_sldl_index(opus_results['transcoded'], index_path)
                    results['index_updates'] += updates
                else:
                    # Find and update all index files in the directory
                    index_files = list(directory.rglob("*.sldl"))
                    logger.info(f"Found {len(index_files)} index files to update")
                    
                    for idx_file in index_files:
                        updates = self._update_sldl_index(opus_results['transcoded'], idx_file)
                        results['index_updates'] += updates
        
        return results
    
    def _transcode_opus_files(self, directory: Path) -> Dict[str, Any]:
        """Find and transcode opus files to the configured output format.
        
        Args:
            directory: Directory to search for opus files
            
        Returns:
            Dictionary with transcoding results
        """
        results = {
            'processed': 0,
            'transcoded': [],
            'errors': []
        }
        
        # Find all opus files
        opus_files = list(directory.rglob("*.opus"))
        
        if not opus_files:
            logger.debug(f"No opus files found in {directory}")
            return results
        
        logger.info(f"Found {len(opus_files)} opus files to transcode")
        
        for opus_file in opus_files:
            try:
                # Determine output file extension based on format
                if self.output_format == 'aac':
                    output_file = opus_file.with_suffix('.m4a')
                else:  # flac
                    output_file = opus_file.with_suffix('.flac')
                
                # Skip if output file already exists
                if output_file.exists():
                    logger.info(f"{self.output_format.upper()} already exists, skipping: {output_file.name}")
                    continue
                
                # Transcode opus to target format
                success = self._transcode_file(opus_file, output_file)
                
                if success:
                    results['transcoded'].append({
                        'original': str(opus_file),
                        'transcoded': str(output_file),
                        'deleted_original': False
                    })
                    
                    # Delete original opus file if configured
                    if self.delete_original:
                        try:
                            opus_file.unlink()
                            results['transcoded'][-1]['deleted_original'] = True
                            logger.info(f"Deleted original opus file: {opus_file.name}")
                        except Exception as e:
                            logger.warning(f"Failed to delete opus file {opus_file}: {e}")
                    
                    results['processed'] += 1
                    logger.info(f"Successfully transcoded: {opus_file.name} -> {output_file.name}")
                else:
                    results['errors'].append(f"Failed to transcode: {opus_file}")
                    
            except Exception as e:
                error_msg = f"Error processing {opus_file}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def _transcode_file(self, input_file: Path, output_file: Path) -> bool:
        """Transcode a single file using ffmpeg.
        
        Args:
            input_file: Input opus file
            output_file: Output file (FLAC or AAC)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build ffmpeg command based on output format
            cmd = ['ffmpeg', '-i', str(input_file)]
            
            if self.output_format == 'aac':
                # AAC encoding options
                cmd.extend([
                    '-c:a', 'aac',
                    '-b:a', f'{self.aac_bitrate}k',
                    '-movflags', '+faststart',  # Optimize for streaming
                ])
            else:  # flac
                # FLAC encoding options
                cmd.extend([
                    '-c:a', 'flac',
                    '-compression_level', str(self.flac_compression_level),
                ])
            
            cmd.extend(['-y', str(output_file)])  # Overwrite output file
            
            logger.debug(f"Transcoding command: {' '.join(cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.debug(f"Transcoding successful: {input_file.name}")
                return True
            else:
                logger.error(f"Transcoding failed for {input_file.name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Transcoding timeout for {input_file.name}")
            return False
        except Exception as e:
            logger.error(f"Transcoding error for {input_file.name}: {e}")
            return False
    
    def _update_sldl_index(self, transcoded_files: List[Dict[str, Any]], index_path: Path):
        """Update the sldl index file with transcoded file information.
        
        Args:
            transcoded_files: List of transcoded file information
            index_path: Path to sldl index file
        """
        if not index_path.exists():
            logger.warning(f"Index file not found: {index_path}")
            return
        
        try:
            # Read the CSV index file
            with open(index_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            updates_made = 0
            
            # Update rows that match transcoded files
            for row in rows:
                filepath = row.get('filepath', '')
                
                # Check if this row matches any transcoded file
                for transcoded in transcoded_files:
                    original_path = Path(transcoded['original'])
                    transcoded_path = Path(transcoded['transcoded'])
                    
                    # Convert to relative paths for comparison
                    # The index uses relative paths like "./filename.opus"
                    original_filename = original_path.name
                    transcoded_filename = transcoded_path.name
                    
                    # Check if the filepath matches the original opus file
                    if (filepath.endswith(original_filename) or 
                        filepath == f"./{original_filename}" or
                        filepath == original_filename):
                        
                        # Update the filepath to point to the transcoded file
                        if filepath.startswith('./'):
                            row['filepath'] = f"./{transcoded_filename}"
                        else:
                            row['filepath'] = transcoded_filename
                        
                        updates_made += 1
                        logger.debug(f"Updated index entry: {filepath} -> {row['filepath']}")
                        break
            
            # Write updated CSV back
            if updates_made > 0:
                with open(index_path, 'w', encoding='utf-8', newline='') as f:
                    if rows:
                        fieldnames = rows[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                
                logger.info(f"Updated {updates_made} entries in sldl index: {index_path}")
            else:
                logger.debug(f"No index entries needed updating in: {index_path}")
                
        except Exception as e:
            logger.error(f"Failed to update sldl index {index_path}: {e}")
            updates_made = 0
        
        return updates_made
    
    def check_ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available for transcoding.
        
        Returns:
            True if ffmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False 
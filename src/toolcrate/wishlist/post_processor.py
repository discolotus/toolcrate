#!/usr/bin/env python3
"""Post-processing module for wishlist downloads."""

import os
import subprocess
import logging
import json
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
        self.transcode_opus = config.get('transcode_opus_to_flac', False)
        self.update_index = config.get('update_index', True)
        self.delete_original = config.get('delete_original_opus', True)
        
    def process_directory(self, directory: Path, index_path: Optional[Path] = None) -> Dict[str, Any]:
        """Process all files in a directory.
        
        Args:
            directory: Directory to process
            index_path: Path to sldl index file
            
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
            'errors': []
        }
        
        if self.transcode_opus:
            opus_results = self._transcode_opus_files(directory)
            results['processed'] += opus_results['processed']
            results['transcoded'].extend(opus_results['transcoded'])
            results['errors'].extend(opus_results['errors'])
            
            # Update index if files were transcoded
            if opus_results['transcoded'] and self.update_index and index_path:
                self._update_sldl_index(opus_results['transcoded'], index_path)
        
        return results
    
    def _transcode_opus_files(self, directory: Path) -> Dict[str, Any]:
        """Find and transcode opus files to FLAC.
        
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
                flac_file = opus_file.with_suffix('.flac')
                
                # Skip if FLAC already exists
                if flac_file.exists():
                    logger.info(f"FLAC already exists, skipping: {flac_file.name}")
                    continue
                
                # Transcode opus to FLAC
                success = self._transcode_file(opus_file, flac_file)
                
                if success:
                    results['transcoded'].append({
                        'original': str(opus_file),
                        'transcoded': str(flac_file),
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
                    logger.info(f"Successfully transcoded: {opus_file.name} -> {flac_file.name}")
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
            output_file: Output FLAC file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use ffmpeg to transcode opus to FLAC
            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-c:a', 'flac',
                '-compression_level', '8',  # Maximum FLAC compression
                '-y',  # Overwrite output file
                str(output_file)
            ]
            
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
            # Read existing index
            with open(index_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            updated_lines = []
            updates_made = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    updated_lines.append(line)
                    continue
                
                # Try to parse the line as JSON
                try:
                    entry = json.loads(line)
                    
                    # Check if this entry matches any transcoded file
                    for transcoded in transcoded_files:
                        original_path = transcoded['original']
                        transcoded_path = transcoded['transcoded']
                        
                        # Update the entry if it matches the original opus file
                        if entry.get('path') == original_path:
                            entry['path'] = transcoded_path
                            entry['transcoded_from_opus'] = True
                            updates_made += 1
                            logger.debug(f"Updated index entry: {original_path} -> {transcoded_path}")
                            break
                    
                    updated_lines.append(json.dumps(entry))
                    
                except json.JSONDecodeError:
                    # Keep non-JSON lines as-is
                    updated_lines.append(line)
            
            # Write updated index back
            if updates_made > 0:
                with open(index_path, 'w', encoding='utf-8') as f:
                    for line in updated_lines:
                        f.write(line + '\n')
                
                logger.info(f"Updated {updates_made} entries in sldl index")
            else:
                logger.debug("No index entries needed updating")
                
        except Exception as e:
            logger.error(f"Failed to update sldl index: {e}")
    
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
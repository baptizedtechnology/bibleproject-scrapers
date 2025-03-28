import logging
import os
import tempfile
from pathlib import Path
import requests
from typing import Optional, Dict, List
import json
import math
import hashlib
from datetime import datetime, timedelta

from openai import OpenAI
from config import OPENAI_API_KEY
from db.supabase import SupabaseManager

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Process audio files using OpenAI's Whisper model"""
    
    def __init__(self, content_type: Optional[str] = None):
        self.content_type = content_type
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.temp_dir = Path(tempfile.gettempdir()) / "bibleproject_audio"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = 25 * 1024 * 1024  # 25 MB in bytes
        self.db = SupabaseManager()
        self.chunk_size = 1000  # Number of characters per chunk
        
    def format_timestamp(self, seconds: float) -> str:
        """
        Format seconds into hh:mm:ss or mm:ss format
        
        Args:
            seconds: Number of seconds
            
        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
        
    def chunk_podcast(self, podcast_id: str) -> bool:
        """
        Chunk a podcast's transcription while preserving timestamps.
        Creates overlapping chunks with 2 segments of overlap between chunks.
        
        Args:
            podcast_id: ID of the podcast to chunk
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get podcast data
            podcast = self.db.get_content_by_id(podcast_id)
            if not podcast:
                logger.error(f"Podcast not found: {podcast_id}")
                return False
                
            # Get the Whisper response
            whisper_data = podcast.get('whisper_json_response')
            if not whisper_data:
                logger.error(f"No Whisper response found for podcast: {podcast_id}")
                return False
                
            # Get segments from Whisper response
            segments = whisper_data.get('metadata', {}).get('segments', [])
            if not segments:
                logger.error(f"No segments found in Whisper response for podcast: {podcast_id}")
                return False
                
            # Initialize chunking variables
            chunk_index = 0
            current_pos = 0
            overlap_size = 2  # Number of segments to overlap
            
            while current_pos < len(segments):
                # Calculate chunk size based on character count
                current_chunk = []
                current_length = 0
                chunk_start_time = segments[current_pos]['start']
                
                # Add segments until we exceed chunk size
                for i in range(current_pos, len(segments)):
                    segment = segments[i]
                    segment_text = segment['text']
                    segment_length = len(segment_text)
                    
                    # If adding this segment would exceed chunk size and we're not at the start
                    if current_length + segment_length > self.chunk_size and current_chunk:
                        # Create chunk metadata
                        chunk_metadata = {
                            'chunk_index': chunk_index,
                            'start_time': self.format_timestamp(chunk_start_time),
                            'end_time': self.format_timestamp(segment['start']),
                            'start_seconds': chunk_start_time,
                            'end_seconds': segment['start'],
                            'timestamp': self.format_timestamp(chunk_start_time),
                            'episode_number': podcast.get('metadata', {}).get('episode_number'),
                            'episode_title': podcast.get('metadata', {}).get('episode_title'),
                            'duration': podcast.get('metadata', {}).get('duration'),
                            'segment_start_index': current_pos,
                            'segment_end_index': i - 1
                        }
                        
                        # Join chunk text
                        chunk_text = ' '.join(current_chunk)
                        
                        # Store chunk in chatbot_sources
                        success = self.db.add_to_chatbot_sources(
                            content=chunk_text,
                            title=f"{podcast['title']}",
                            source_url=podcast['source_url'],
                            content_type='podcast',
                            metadata=chunk_metadata,
                            content_index_id=podcast_id
                        )
                        
                        if not success:
                            logger.error(f"Failed to store chunk {chunk_index} for podcast: {podcast['title']}")
                            return False
                            
                        # Move position forward, accounting for overlap
                        current_pos = max(0, i - overlap_size)  # Ensure we don't go negative
                        chunk_index += 1
                        break
                    else:
                        current_chunk.append(segment_text)
                        current_length += segment_length
                        
                        # If we're at the last segment, create the final chunk
                        if i == len(segments) - 1:
                            chunk_metadata = {
                                'chunk_index': chunk_index,
                                'start_time': self.format_timestamp(chunk_start_time),
                                'end_time': self.format_timestamp(segment['end']),
                                'start_seconds': chunk_start_time,
                                'end_seconds': segment['end'],
                                'timestamp': self.format_timestamp(chunk_start_time),
                                'episode_number': podcast.get('metadata', {}).get('episode_number'),
                                'episode_title': podcast.get('metadata', {}).get('episode_title'),
                                'duration': podcast.get('metadata', {}).get('duration'),
                                'segment_start_index': current_pos,
                                'segment_end_index': i
                            }
                            
                            chunk_text = ' '.join(current_chunk)
                            
                            success = self.db.add_to_chatbot_sources(
                                content=chunk_text,
                                title=f"{podcast['title']}",
                                source_url=podcast['source_url'],
                                content_type='podcast',
                                metadata=chunk_metadata,
                                content_index_id=podcast_id
                            )
                            
                            if not success:
                                logger.error(f"Failed to store final chunk for podcast: {podcast['title']}")
                                return False
                                
                            current_pos = len(segments)  # Exit the loop
                            chunk_index += 1
                    
            # Update podcast status to processed
            self.db.update_content_status(podcast_id, 'processed')
            
            logger.info(f"Successfully chunked podcast: {podcast['title']} into {chunk_index} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error chunking podcast {podcast_id}: {e}")
            return False
            
    def process_pending_podcasts(self, limit: int = 40) -> int:
        """
        Process podcasts with 'pending' status, chunk them, and store in chatbot_sources
        
        Args:
            limit: Maximum number of podcasts to process
            
        Returns:
            Number of successfully processed podcasts
        """
        logger.info(f"Processing up to {limit} pending podcasts")
        
        # Fetch podcasts with 'pending' status
        pending_podcasts = self.db.get_content_by_status('pending', content_type='podcast', limit=limit)
        
        if not pending_podcasts:
            logger.info("No pending podcasts found to process")
            return 0
            
        logger.info(f"Found {len(pending_podcasts)} pending podcasts to process")
        processed_count = 0
        
        for podcast in pending_podcasts:
            logger.info(f"Processing podcast: {podcast['title']}")
            
            if self.chunk_podcast(podcast['id']):
                processed_count += 1
            else:
                logger.error(f"Failed to process podcast: {podcast['title']}")
                
        logger.info(f"Processed {processed_count} out of {len(pending_podcasts)} podcasts")
        return processed_count
        
    def download_audio(self, url: str) -> Optional[Path]:
        """
        Download audio file from URL to temp directory
        
        Args:
            url: URL of the audio file
            
        Returns:
            Path to downloaded file or None if download failed
        """
        try:
            # Generate a unique filename
            filename = f"podcast_{hash(url)}.mp3"
            filepath = self.temp_dir / filename
            
            # Download the file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            logger.info(f"Downloaded audio file to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error downloading audio file from {url}: {e}")
            return None
            
    def split_audio(self, audio_path: Path) -> List[Path]:
        """
        Split audio file into chunks if it exceeds max file size
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of paths to audio chunks
        """
        try:
            file_size = os.path.getsize(audio_path)
            
            # If file is small enough, return as is
            if file_size <= self.max_file_size:
                return [audio_path]
            
            # Calculate number of chunks needed
            num_chunks = math.ceil(file_size / self.max_file_size)
            chunk_size = file_size // num_chunks
            
            chunks = []
            with open(audio_path, 'rb') as f:
                for i in range(num_chunks):
                    chunk_path = self.temp_dir / f"{audio_path.stem}_chunk_{i}.mp3"
                    with open(chunk_path, 'wb') as chunk_file:
                        # Read chunk_size bytes
                        chunk_data = f.read(chunk_size)
                        chunk_file.write(chunk_data)
                    chunks.append(chunk_path)
                    
            logger.info(f"Split audio into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting audio file {audio_path}: {e}")
            return []
            
    def transcribe_audio(self, audio_path: Path) -> Optional[Dict]:
        """
        Transcribe audio file using Whisper model
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict containing transcription and timestamps or None if transcription failed
        """
        try:
            # Open the audio file
            with open(audio_path, "rb") as audio_file:
                # Call Whisper API with segment-level timestamps
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
  file=audio_file,
  response_format="verbose_json",
  timestamp_granularities=["segment"]
)

                return response
                
        except Exception as e:
            logger.error(f"Error transcribing audio file {audio_path}: {e}")
            return None
            
    def combine_transcriptions(self, transcriptions: List[Dict]) -> Dict:
        """
        Combine multiple transcriptions into a single result
        
        Args:
            transcriptions: List of transcription results
            
        Returns:
            Combined transcription result
        """
        if not transcriptions:
            return None
            
        # Combine all segments
        all_segments = []
        for i, trans in enumerate(transcriptions):
            # Adjust timestamps based on chunk position
            for segment in trans.segments:
                # Add offset based on chunk position
                offset = i * 600  # 10 minutes in seconds
                segment.start += offset
                segment.end += offset
                all_segments.append(segment)
                
        # Sort segments by start time
        all_segments.sort(key=lambda x: x.start)
        
        # Combine text
        full_text = " ".join(segment.text for segment in all_segments)
        
        # Create metadata
        metadata = {
  "segments": [
    {
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end,
                    "avg_logprob": segment.avg_logprob if hasattr(segment, 'avg_logprob') else None
                }
                for segment in all_segments
            ]
        }
        
        return {
            "text": full_text,
            "metadata": metadata
        }
            
    def save_transcription(self, transcription: Dict, output_path: Path) -> bool:
        """
        Save transcription to a text file
        
        Args:
            transcription: Dict containing transcription text and metadata
            output_path: Path to save the transcription
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write the full text
                f.write("=== Full Transcription ===\n\n")
                f.write(transcription["text"])
                f.write("\n\n=== Segments with Timestamps ===\n\n")
                
                # Write each segment with its timestamp
                for segment in transcription["metadata"]["segments"]:
                    f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] ")
                    f.write(f"{segment['text']}\n")
                    
            logger.info(f"Saved transcription to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving transcription to {output_path}: {e}")
            return False
            
    def process_audio(self, url: str) -> Optional[Dict]:
        """
        Process audio file: download, transcribe, and save result
        
        Args:
            url: URL of the audio file
            
        Returns:
            Dict containing transcription and metadata or None if processing failed
        """
        # Download audio file
        audio_path = self.download_audio(url)
        if not audio_path:
            return None
            
        # Split audio if needed
        chunks = self.split_audio(audio_path)
        if not chunks:
            return None
            
        # Transcribe each chunk
        transcriptions = []
        for chunk_path in chunks:
            transcription = self.transcribe_audio(chunk_path)
            if transcription:
                transcriptions.append(transcription)
                
        if not transcriptions:
            return None
            
        # # Save transcription to temp file for testing
        # output_path = self.temp_dir / f"transcription_{audio_path.stem}.txt"
        # if not self.save_transcription(combined, output_path):
        #     return None
            
        return self.combine_transcriptions(transcriptions)
        
    def process_new_podcasts(self, limit: int = 40) -> int:
        """
        Process podcasts with 'new' status, transcribe them, and update their status to 'pending'.
        Stores the transcription in 'content' column of database for chunking and the full Whisper response
        in 'whisper_json_response' for future reference.
        
        Args:
            limit: Maximum number of podcasts to process
            
        Returns:
            Number of successfully processed podcasts
        """
        logger.info(f"Processing up to {limit} new podcasts")
        
        # Fetch podcasts with 'new' status
        new_podcasts = self.db.get_content_by_status('new', content_type='podcast', limit=limit)
        
        if not new_podcasts:
            logger.info("No new podcasts found to process")
            return 0
            
        logger.info(f"Found {len(new_podcasts)} new podcasts to process")
        processed_count = 0
        
        for podcast in new_podcasts:
            logger.info(f"Processing podcast: {podcast['title']}")
            
            # Get the download URL
            download_url = podcast['download_url']
            if not download_url:
                logger.error(f"No download URL for podcast {podcast['id']}")
                continue
                
            # Process the audio
            result = self.process_audio(download_url)
            if not result:
                logger.error(f"Failed to process podcast audio: {podcast['title']}")
                # Mark as failed
                self.db.update_content_status(podcast['id'], 'failed')
                continue
                
            # Generate a hash of the transcription text
            content_hash = hashlib.md5(result['text'].encode()).hexdigest()
            
            # Update the database with transcription, hash, and full Whisper response
            success = self.db.update_content(
                content_id=podcast['id'],
                content=result['text'],
                content_hash=content_hash,
                status='pending',
                metadata=podcast['metadata'],  # Keep existing metadata
                whisper_json_response=result  # Store the full Whisper response
            )
            
            if success:
                logger.info(f"Successfully processed podcast: {podcast['title']}")
                processed_count += 1
            else:
                logger.error(f"Failed to update database for podcast: {podcast['title']}")
                
        logger.info(f"Processed {processed_count} out of {len(new_podcasts)} podcasts")
        return processed_count
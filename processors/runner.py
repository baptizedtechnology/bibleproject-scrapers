import logging
from typing import Optional

from processors.text import TextProcessor
from processors.audio import AudioProcessor
import config

logger = logging.getLogger(__name__)

def process_pending_content(content_type: Optional[str] = None, limit: int = 40) -> int:
    """
    Process pending content in the database
    
    Args:
        content_type: Type of content to process (None for all types)
        limit: Maximum number of items to process
        
    Returns:
        Number of successfully processed items
    """
    total_processed = 0
    
    # Initialize processors based on content type
    if content_type in [None, 'article', 'book', 'text', 'research_paper', 'blog', 'website', 'bible']:
        text_processor = TextProcessor()
        processed = text_processor.process_pending_items(limit=limit)
        total_processed += processed
        logger.info(f"Processed {processed} text items")
    
    if content_type in [None, 'podcast', 'speech', 'video']:
        audio_processor = AudioProcessor()
        # Process new podcasts (audio files that need transcription)
        processed_new = audio_processor.process_new_podcasts(limit=limit)
        processed_pending = audio_processor.process_pending_podcasts(limit=limit)
        total_processed += processed_new + processed_pending
        logger.info(f"Processed {processed_new} new podcast items")
        logger.info(f"Processed {processed_pending} pending podcast items")
    
    return total_processed
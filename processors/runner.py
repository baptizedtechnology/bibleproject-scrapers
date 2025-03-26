import logging
from typing import Optional

from processors.text import TextProcessor
# from processors.audio import AudioProcessor
import config

logger = logging.getLogger(__name__)

def process_pending_content(content_type: Optional[str] = None, limit: int = 10) -> int:
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
        # Audio processor not fully implemented yet
        # audio_processor = AudioProcessor()
        # processed = audio_processor.process_pending_items(limit=limit)
        # total_processed += processed
        logger.info("Audio processing not yet implemented")
    
    return total_processed
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from db.supabase import SupabaseManager

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """
    Base class for content processors with common functionality
    
    Designed for reuse across projects - this file can be extracted
    into a shared library after project completion.
    """
    def __init__(self, content_type: Optional[str] = None):
        """
        Initialize processor
        
        Args:
            content_type: Type of content this processor handles (None for all types). Defaults to None.
        """
        self.content_type = content_type
        self.db = SupabaseManager()
    
    @abstractmethod
    def process_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Process raw content into chunks suitable for the RAG system
        
        Args:
            content: Raw content text
            metadata: Content metadata
            
        Returns:
            List of processed content chunks
        """
        pass
        
    def process_pending_items(self, limit: int = 10) -> int:
        """
        Process pending items from the database for this content type
        
        Args:
            limit: Maximum number of items to process
            
        Returns:
            Number of successfully processed items
        """

        #Returns DB entries from 'scrape_content_index' table that are pending
        pending_items = self.db.get_pending_content(content_type=self.content_type, limit=limit)
        processed_count = 0
        
        for item in pending_items:
            try:
                # Process the content into chunks
                content = item.get('text_content', '')
                metadata = item.get('metadata', {})
                
                if not content:
                    logger.warning(f"Empty content for item {item['id']}")
                    self.db.update_content_status(item['id'], 'failed', chatbot_source_id=None)
                    continue
                
                # Process content returns a list of dicts with 'text' and 'metadata'
                chunk_objects = self.process_content(content, metadata)
                
                # Store each chunk in the database
                for i, chunk_obj in enumerate(chunk_objects):
                    chunk_text = chunk_obj['text']
                    chunk_metadata = chunk_obj['metadata']
                    
                    # Add original content ID to metadata
                    chunk_metadata['original_content_id'] = item['id']
                    
                    # Create a title for this chunk
                    chunk_title = f"{item.get('title', 'Untitled')}"
                    
                    # Add to chatbot sources
                    #ChatbotID is handled in the 'add_to_chatbot_sources' function
                    link_url = item.get('source_url') or item.get('download_url')
                    chatbot_source_id = self.db.add_to_chatbot_sources(
                        content=chunk_text,
                        title=chunk_title,
                        source_url=link_url,
                        content_type=item['content_type'],
                        metadata=chunk_metadata,
                        content_index_id=item['id']
                    )
                
                # Mark as processed
                self.db.update_content_status(
                    item['id'], 
                    'processed', 
                    processed_content=None,
                    chatbot_source_id=None
                )
                
                processed_count += 1
                
            except Exception as e:
                logger.exception(f"Error processing item {item['id']}: {e}")
                self.db.update_content_status(item['id'], 'failed')
        
        return processed_count
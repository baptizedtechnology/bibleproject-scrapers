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
    def __init__(self, content_type: str):
        """
        Initialize processor
        
        Args:
            content_type: Type of content this processor handles
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
        pending_items = self.db.get_pending_content(content_type=self.content_type, limit=limit)
        processed_count = 0
        
        for item in pending_items:
            try:
                # Process the content into chunks
                content = item.get('content', '')
                metadata = item.get('metadata', {})
                
                if not content:
                    logger.warning(f"Empty content for item {item['id']}")
                    self.db.update_content_status(item['id'], 'failed', chatbot_source_id=None)
                    continue
                
                chunks = self.process_content(content, metadata)
                
                # Store each chunk in the database
                for i, chunk in enumerate(chunks):
                    # Update metadata with chunk info
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'original_content_id': item['id']
                    })
                    
                    # Create a title for this chunk
                    chunk_title = f"{item.get('title', 'Untitled')} (Part {i+1}/{len(chunks)})"
                    
                    # Add to chatbot sources
                    # In a real implementation, this would include embedding generation
                    chatbot_source_id = self.db.add_to_chatbot_sources(
                        content=chunk,
                        title=chunk_title,
                        source_url=item['url'],
                        content_type=self.content_type,
                        metadata=chunk_metadata,
                        content_index_id=item['id']
                    )
                
                # Mark as processed
                self.db.update_content_status(
                    item['id'], 
                    'processed', 
                    processed_content=None,  # We don't need to store the processed content again
                    chatbot_source_id=None  # We created multiple sources, so no single ID
                )
                
                processed_count += 1
                
            except Exception as e:
                logger.exception(f"Error processing item {item['id']}: {e}")
                self.db.update_content_status(item['id'], 'failed')
        
        return processed_count
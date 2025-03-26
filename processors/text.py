import logging
import re
from typing import Dict, Any, List, Optional

from processors.base import BaseProcessor
from utils.helpers import split_text_into_chunks
from config import MAX_CONTENT_CHUNK_SIZE

logger = logging.getLogger(__name__)

class TextProcessor(BaseProcessor):
    """
    Processor for text content (including extracted PDF text)
    
    Designed for reuse across projects - this file can be extracted
    into a shared library after project completion.
    """
    def __init__(self, content_type: Optional[str] = None):
        super().__init__(content_type=content_type)
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        # Convert multiple whitespace to single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize quotation marks
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Fix common OCR/PDF extraction issues
        text = text.replace('fi', 'fi')  # Fix for ligatures
        text = text.replace('fl', 'fl')  # Fix for ligatures
        
        # Normalize newlines
        text = text.replace('\r\n', '\n')
        
        # Remove page numbers
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Remove headers/footers (simplified - real implementation would be more complex)
        text = re.sub(r'\n[^a-zA-Z0-9]*BibleProject[^a-zA-Z0-9]*\n', '\n', text)
        
        return text.strip()
    
    #FIXME: This will need to be updated to handle different types of text content since we need different metadata for each
    def process_content(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process text content into chunks suitable for the RAG system
        
        Args:
            content: Raw text content
            metadata: Content metadata
            
        Returns:
            List of processed chunk objects with text and metadata
        """
        
        # Clean the text
        cleaned_text = self.clean_text(content)
        
        # Get the text to chunk
        text_to_chunk = cleaned_text
        
        # Split into chunks with page information
        chunk_objects = split_text_into_chunks(text_to_chunk, 
                                            max_size=MAX_CONTENT_CHUNK_SIZE,
                                            overlap=200)
        
        # Create full chunk objects with metadata
        processed_chunks = []
        for i, chunk_obj in enumerate(chunk_objects):
            # Update metadata with chunk information
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunk_objects),
                'page': chunk_obj.get('page', None)
            })
            
            # Add the processed chunk
            processed_chunks.append({
                'text': chunk_obj['text'],
                'metadata': chunk_metadata
            })
        
        logger.info(f"Split content into {len(processed_chunks)} chunks")
        return processed_chunks
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
    def __init__(self):
        super().__init__(content_type='text')
    
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
    
    def extract_structured_content(self, text: str) -> Dict[str, Any]:
        """
        Extract structured information from text when possible
        
        Args:
            text: Cleaned text content
            
        Returns:
            Dictionary with extracted structure
        """
        result = {'full_text': text}
        
        # Try to extract title
        title_match = re.match(r'^(.*?)\n', text)
        if title_match:
            result['extracted_title'] = title_match.group(1).strip()
        
        # Try to extract sections (simplified)
        sections = []
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            # Simple heuristic for section headers: short, uppercase lines
            if len(line) < 50 and line.isupper() and line.strip():
                # Save previous section
                if current_section:
                    sections.append({
                        'heading': current_section,
                        'content': '\n'.join(current_content)
                    })
                
                # Start new section
                current_section = line.strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Don't forget the last section
        if current_section:
            sections.append({
                'heading': current_section,
                'content': '\n'.join(current_content)
            })
        
        if sections:
            result['sections'] = sections
        
        return result
    
    def process_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Process text content into chunks suitable for the RAG system
        
        Args:
            content: Raw text content
            metadata: Content metadata
            
        Returns:
            List of processed content chunks
        """
        # Clean the text
        cleaned_text = self.clean_text(content)
        
        # Extract structure if possible
        structured_content = self.extract_structured_content(cleaned_text)
        
        # Get the text to chunk
        text_to_chunk = structured_content.get('full_text', cleaned_text)
        
        # Split into chunks
        chunks = split_text_into_chunks(text_to_chunk, 
                                       max_size=MAX_CONTENT_CHUNK_SIZE,
                                       overlap=200)
        
        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks
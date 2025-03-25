import logging
import re
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import fitz  # PyMuPDF for PDF processing

logger = logging.getLogger(__name__)

def clean_filename(filename: str) -> str:
    """
    Clean a string to make it safe for use as a filename
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Replace invalid characters with underscore
    clean = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Replace multiple spaces/underscores with single
    clean = re.sub(r'[_\s]+', '_', clean)
    # Remove leading/trailing underscores and spaces
    return clean.strip('_').strip()

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text or empty string if failed
    """
    try:
        import fitz  # PyMuPDF
        
        text = ""
        page_texts = []
        
        with fitz.open(pdf_path) as doc:
            total_pages = len(doc)
            
            for i, page in enumerate(doc):
                page_text = page.get_text()
                page_texts.append(page_text)
                text += page_text
                
                # Add page markers for later chunking reference
                if i < total_pages - 1:
                    text += f"\n[PAGE_BREAK_{i+1}]\n"
        
        return text
    except Exception as e:
        logging.exception(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

def split_text_into_chunks(text: str, max_size: int = 4000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of approximately max_size characters
    
    Args:
        text: Text to split
        max_size: Maximum chunk size in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of text chunks
    """
    # Split text by paragraphs
    paragraphs = re.split(r'\n{2,}', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        paragraph_size = len(paragraph)
        
        # If this paragraph alone exceeds max size, we need to split it further
        if paragraph_size > max_size:
            # If we have content in current chunk, add it first
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split large paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            
            sent_chunk = []
            sent_size = 0
            
            for sentence in sentences:
                if sent_size + len(sentence) <= max_size or not sent_chunk:
                    sent_chunk.append(sentence)
                    sent_size += len(sentence) + 1  # +1 for space
                else:
                    chunks.append(' '.join(sent_chunk))
                    
                    # Create overlap with previous chunk
                    overlap_point = max(0, len(sent_chunk) - int(overlap / 10))
                    sent_chunk = sent_chunk[overlap_point:]
                    sent_size = sum(len(s) + 1 for s in sent_chunk)
                    
                    sent_chunk.append(sentence)
                    sent_size += len(sentence) + 1
            
            if sent_chunk:
                chunks.append(' '.join(sent_chunk))
                
        # Regular paragraph handling
        elif current_size + paragraph_size <= max_size:
            current_chunk.append(paragraph)
            current_size += paragraph_size + 2  # +2 for paragraph break
        else:
            # Current chunk is full, store it
            chunks.append('\n\n'.join(current_chunk))
            
            # Start a new chunk with overlap if possible
            overlap_size = 0
            overlap_chunks = []
            
            # Look back through paragraphs for overlap
            for i in range(len(current_chunk) - 1, -1, -1):
                p = current_chunk[i]
                if overlap_size + len(p) <= overlap:
                    overlap_chunks.insert(0, p)
                    overlap_size += len(p) + 2
                else:
                    break
            
            current_chunk = overlap_chunks + [paragraph]
            current_size = sum(len(p) + 2 for p in current_chunk)
    
    # Don't forget any remaining text
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

def get_metadata_template(content_type: str) -> Dict[str, Any]:
    """
    Get a metadata template with required fields for a specific content type
    
    Args:
        content_type: Type of content (book, podcast, etc.)
        
    Returns:
        Dict: Template with required metadata fields initialized with None
    """
    templates = {
        'book': {
            'isbn': None,
            'publisher': None, 
            'publication_year': None,
            'author': None,
            'page': None
        },
        'podcast': {
            'episode_number': None,
            'episode_title': None,
            'timestamp': None,
            'duration': None
        },
        'article': {
            'page': None,
            'publication_date': None,
            'author': None
        },
        'video': {
            'timestamp': None,
            'platform': None,
            'video_length': None
        },
        'speech': {
            'speaker': None,
            'speech_date': None
        },
        'research_paper': {
            'title': None,
            'author': None,
            'publication_year': None,
            'journal_name': None,
            'doi': None
        },
        'blog': {
            'author': None,
            'publication_date': None,
            'url': None
        },
        'website': {
            'url': None,
            'author': None
        },
        'bible': {
            'verse': None,
            'chapter': None,
            'book': None,
            'translation': None
        }
    }
    
    # Return requested template or empty dict if type not found
    return templates.get(content_type, {}).copy()

def merge_metadata(base_metadata: Dict[str, Any], 
                  new_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new metadata into base metadata
    
    Args:
        base_metadata: Base metadata dictionary
        new_metadata: New metadata to merge
        
    Returns:
        Dict: Merged metadata dictionary
    """
    # Update base metadata with new metadata
    base_metadata.update(new_metadata)
    
    return base_metadata

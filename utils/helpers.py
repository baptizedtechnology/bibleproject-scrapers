import logging
import re
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai

logger = logging.getLogger(__name__)

def create_embedding(text: str) -> List[float]:
    """
    Create an embedding vector for the given text
    
    Args:
        text: Text to create embedding for
        
    Returns:
        List of floats representing the embedding vector
    """
    try:
        from config import OPENAI_API_KEY
        
        # Set OpenAI API key
        openai.api_key = OPENAI_API_KEY
        
        # Create embedding
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        
        # Return the embedding vector
        return response.data[0].embedding
        
    except Exception as e:
        logger.exception(f"Error creating embedding: {e}")
        # Return a zero vector as fallback (not ideal but prevents crashes)
        return [0.0] * 1536  # Current dimension for OpenAI embeddings

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

def split_text_into_chunks(text: str, max_size: int = 4000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks of approximately max_size characters
    
    Args:
        text: Text to split
        max_size: Maximum chunk size in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of dictionaries with text and page information
    """
    # Create a map of character positions to page numbers
    page_map = {}
    page_breaks = []
    current_page = 1
    
    # Find all page break positions in the original text
    for match in re.finditer(r'\[PAGE_BREAK_(\d+)\]', text):
        page_num = int(match.group(1))
        position = match.start()
        page_breaks.append((position, page_num))
    
    # Sort page breaks by position
    page_breaks.sort(key=lambda x: x[0])
    
    # Remove page markers for clean text
    clean_text = re.sub(r'\[PAGE_BREAK_\d+\]', '', text)
    
    # Calculate offset map to convert between original and clean text positions
    offset_map = []  # List of (original_pos, clean_text_pos)
    clean_pos = 0
    for i, char in enumerate(text):
        if not text[i:].startswith('[PAGE_BREAK_'):
            offset_map.append((i, clean_pos))
            clean_pos += 1
    
    # Build the page map for clean text positions
    for i in range(len(offset_map)):
        orig_pos = offset_map[i][0]
        clean_pos = offset_map[i][1]
        
        # Find the current page based on original position
        current_page = 1  # Default page
        for break_pos, page_num in page_breaks:
            if orig_pos >= break_pos:
                current_page = page_num
        
        page_map[clean_pos] = current_page
    
    # Split text by paragraphs
    paragraphs = re.split(r'\n{2,}', clean_text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    current_position = 0  # Position in clean text
    
    for paragraph in paragraphs:
        paragraph_size = len(paragraph)
        
        # Determine page for this paragraph (use start position)
        paragraph_page = page_map.get(current_position, 1)
        
        # If this paragraph alone exceeds max size, split it further
        if paragraph_size > max_size:
            # If we have content in current chunk, add it first
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunk_page = page_map.get(current_position - current_size, 1)
                chunks.append({
                    'text': chunk_text,
                    'page': chunk_page
                })
                current_chunk = []
                current_size = 0
            
            # Split large paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            
            sent_chunk = []
            sent_size = 0
            sent_position = current_position
            
            for sentence in sentences:
                if sent_size + len(sentence) <= max_size or not sent_chunk:
                    sent_chunk.append(sentence)
                    sent_size += len(sentence) + 1  # +1 for space
                else:
                    chunk_text = ' '.join(sent_chunk)
                    # Get page at start of sentence chunk
                    sent_chunk_page = page_map.get(sent_position, paragraph_page)
                    chunks.append({
                        'text': chunk_text,
                        'page': sent_chunk_page
                    })
                    
                    # Create overlap with previous chunk
                    overlap_point = max(0, len(sent_chunk) - int(overlap / 10))
                    sent_chunk = sent_chunk[overlap_point:]
                    sent_size = sum(len(s) + 1 for s in sent_chunk)
                    
                    # Update sent_position based on overlap
                    overlap_chars = sum(len(s) + 1 for s in sent_chunk[:overlap_point])
                    sent_position += overlap_chars
                    
                    sent_chunk.append(sentence)
                    sent_size += len(sentence) + 1
            
            if sent_chunk:
                chunk_text = ' '.join(sent_chunk)
                chunks.append({
                    'text': chunk_text,
                    'page': paragraph_page
                })
                
            current_position += paragraph_size + 2  # +2 for paragraph break
            
        # Regular paragraph handling
        elif current_size + paragraph_size <= max_size:
            current_chunk.append(paragraph)
            current_size += paragraph_size + 2  # +2 for paragraph break
            current_position += paragraph_size + 2
        else:
            # Current chunk is full, store it
            chunk_text = '\n\n'.join(current_chunk)
            # Get page at start of chunk
            chunk_start_position = current_position - current_size
            chunk_page = page_map.get(chunk_start_position, 1)
            chunks.append({
                'text': chunk_text,
                'page': chunk_page
            })
            
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
            
            # Adjust position to account for overlap
            overlap_chars = sum(len(p) + 2 for p in overlap_chunks)
            current_position = current_position - overlap_chars + paragraph_size + 2
    
    # Don't forget any remaining text
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        # Get page at start of final chunk
        chunk_start_position = current_position - current_size
        chunk_page = page_map.get(chunk_start_position, 1)
        chunks.append({
            'text': chunk_text,
            'page': chunk_page
        })
    
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

def cleanup_temp_files(min_age_hours: float = 0, file_types: List[str] = None) -> int:
    """
    Delete temporary files from the TEMP_DIR that are no longer needed
    
    Args:
        min_age_hours: Minimum age of files to delete in hours (0 for all files)
        file_types: List of file extensions to delete (e.g. ['.pdf', '.mp3']) or None for all
        
    Returns:
        int: Number of files deleted
    """
    from pathlib import Path
    from config import TEMP_DIR
    import time
    import os
    
    if not TEMP_DIR.exists():
        return 0
    
    current_time = time.time()
    min_age_seconds = min_age_hours * 3600
    deleted_count = 0
    
    try:
        for file_path in TEMP_DIR.glob('*'):
            if not file_path.is_file():
                continue
                
            # Check file age
            file_age = current_time - file_path.stat().st_mtime
            if file_age < min_age_seconds:
                continue
                
            # Check file type
            if file_types and file_path.suffix.lower() not in file_types:
                continue
                
            # Delete the file
            try:
                os.remove(file_path)
                logger.info(f"Deleted temporary file: {file_path.name}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not delete file {file_path.name}: {e}")
                
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")
        return deleted_count

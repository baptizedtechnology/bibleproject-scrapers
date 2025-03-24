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

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text content from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text
    """
    try:
        text_content = []
        
        # Open the PDF
        with fitz.open(pdf_path) as pdf:
            # Process each page
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                # Extract text from the page
                text = page.get_text()
                text_content.append(text)
        
        # Join all pages
        full_text = "\n".join(text_content)
        
        # Basic cleanup
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Remove excessive newlines
        
        return full_text
        
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
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

def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extract metadata from a study notes filename
    
    Args:
        filename: PDF filename
        
    Returns:
        Dictionary of metadata
    """
    metadata = {
        "source": "BibleProject Study Notes",
        "document_type": "study_notes",
        "extracted_date": datetime.now().isoformat()
    }
    
    # Extract book name if present
    book_match = re.search(r'(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|'
                           r'1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|'
                           r'Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|'
                           r'Song of Songs|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|'
                           r'Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|'
                           r'Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|'
                           r'1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|'
                           r'Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|'
                           r'Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|'
                           r'3 John|Jude|Revelation)', filename, re.IGNORECASE)
    
    if book_match:
        metadata["book"] = book_match.group(1)
    
    # Extract series/theme if present
    theme_match = re.search(r'(Torah|Wisdom|Prophets|Gospel|Epistles|Apocalyptic|'
                           r'Biblical Themes|Character|Word Study)', filename, re.IGNORECASE)
    
    if theme_match:
        metadata["theme"] = theme_match.group(1)
        
    return metadata
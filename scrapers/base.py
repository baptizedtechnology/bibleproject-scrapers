import logging
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import USER_AGENT, REQUEST_DELAY, REQUEST_TIMEOUT, TEMP_DIR
from db.supabase import SupabaseManager

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Base class for all scrapers with common functionality
    """
    def __init__(self, name: str):
        self.name = name
        self.source_type = name.lower()
        self.db = SupabaseManager()
        self.session = self._init_session()
        self.items_found = 0
        self.items_new = 0
        
    def _init_session(self) -> requests.Session:
        """Initialize and configure a requests session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        return session
    
    def make_request(self, url: str, method: str = 'GET', 
                    params: Dict = None, data: Dict = None, 
                    retry_count: int = 3, retry_delay: int = 5) -> Optional[requests.Response]:
        """
        Make an HTTP request with rate limiting and retry logic
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            params: URL parameters
            data: Form data for POST requests
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
            
        Returns:
            Response object or None if all retries failed
        """
        # Rate limiting delay
        time.sleep(REQUEST_DELAY)
        
        for attempt in range(retry_count + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response
            
            except (requests.RequestException, requests.Timeout) as e:
                if attempt == retry_count:
                    logger.error(f"Failed request to {url} after {retry_count} retries: {e}")
                    return None
                
                logger.warning(f"Request to {url} failed (attempt {attempt+1}/{retry_count+1}): {e}")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
        return None
    
    def download_file(self, url: str, filename: str) -> Optional[Path]:
        """
        Download a file from URL to the temp directory
        
        Args:
            url: URL of the file to download
            filename: Name to save the file as
            
        Returns:
            Path to downloaded file or None if download failed
        """
        filepath = TEMP_DIR / filename
        
        try:
            response = self.make_request(url, stream=True)
            if not response:
                return None
                
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            logger.info(f"Downloaded file to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    def add_content(self, url: str, content: str, title: str = None, 
                   content_type: str = 'text', metadata: Dict = None) -> bool:
        """
        Add new content to the index if not already present
        
        Args:
            url: Content URL
            content: The content text
            title: Content title
            content_type: Type of content
            metadata: Additional metadata
            
        Returns:
            bool: True if content was added, False otherwise
        """
        result = self.db.add_content_to_index(
            url=url,
            content=content,
            title=title,
            content_type=content_type,
            metadata=metadata
        )
        
        if result:
            self.items_new += 1
            return True
        return False
        
    def record_scrape_results(self, status: str = 'completed', error: str = None) -> None:
        """Record the results of this scraping operation"""
        self.db.record_scrape_operation(
            source_type=self.source_type,
            items_found=self.items_found,
            items_new=self.items_new,
            status=status,
            error=error
        )
    
    @abstractmethod
    def scrape(self) -> bool:
        """
        Main scraping method to be implemented by subclasses
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        pass
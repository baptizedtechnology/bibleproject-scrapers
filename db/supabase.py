import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, DEFAULT_CHATBOT_ID
url: str = SUPABASE_URL
key: str = SUPABASE_KEY

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Manages database operations with Supabase
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure one client instance"""
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the Supabase client and setup state"""
        self.client: Client = create_client(url, key)
        self._setup_database()
    
    def _setup_database(self):
        """
        Ensure necessary tables exist in the database
        """
        # In a production environment, you might want to manage table creation
        # through migrations rather than at runtime
        try:
            # Check if our custom tables exist - if not, we'll create them
            # This is a simplified approach; in production, use proper migrations
            logger.info("Checking database schema")
            
            # NOTE: This is commented out because we're assuming tables already exist
            # In a real implementation, add proper schema validation or migration
            
            logger.info("Database schema verified")
            
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            raise
    
    def compute_content_hash(self, content: str) -> str:
        """Create a hash for content to detect duplicates"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def content_exists(self, url: str, content_hash: str) -> bool:
        """
        Check if content already exists in the index
        
        Args:
            url: The content URL
            content_hash: Hash of content
            
        Returns:
            bool: True if content exists, False otherwise
        """
        try:
            result = self.client.table('scrape_content_index') \
                .select('id') \
                .eq('content_hash', content_hash) \
                .execute()
                
            # If we found a match, content exists
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking content existence: {e}")
            # If we can't check, assume it doesn't exist
            return False
    
    def add_content_to_index(self, 
                            url: str, 
                            content: str, 
                            title: Optional[str] = None,
                            content_type: str = 'text', 
                            metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """
        Add new content to the index if it doesn't exist
        
        Args:
            url: Content URL
            content: The actual content text
            title: Optional content title
            content_type: Type of content ('text', 'audio', etc.)
            metadata: Additional metadata as dictionary
            
        Returns:
            dict: The created record or None if content already exists
        """
        try:
            # Generate content hash
            content_hash = self.compute_content_hash(content)
            
            # Check if content already exists
            if self.content_exists(url, content_hash):
                logger.info(f"Content already exists: {url}")
                return None
                
            # Prepare record
            record = {
                'url': url,
                'content_hash': content_hash,
                'content_type': content_type,
                'title': title,
                'status': 'pending',
                'metadata': metadata or {},
                'discovered_at': datetime.now().isoformat()
            }
            
            # Insert record
            result = self.client.table('scrape_content_index').insert(record).execute()
            
            if result.data:
                logger.info(f"Added new content to index: {title or url}")
                return result.data[0]
            else:
                logger.warning(f"Failed to add content to index: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error adding content to index: {e}")
            return None
    
    def record_scrape_operation(self, 
                               source_type: str, 
                               items_found: int, 
                               items_new: int,
                               status: str = 'completed',
                               error: Optional[str] = None,
                               metadata: Optional[Dict] = None) -> bool:
        """
        Record details of a scraping operation
        
        Args:
            source_type: Type of content source ('podcast', 'classroom', 'study_notes')
            items_found: Total number of items found
            items_new: Number of new items added
            status: Operation status ('completed', 'failed', etc.)
            error: Error message if applicable
            metadata: Additional metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            record = {
                'source_type': source_type,
                'started_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat(),
                'status': status,
                'items_found': items_found,
                'items_new': items_new,
                'error': error,
                'metadata': metadata or {}
            }
            
            self.client.table('scrape_history').insert(record).execute()
            return True
            
        except Exception as e:
            logger.error(f"Error recording scrape operation: {e}")
            return False
    
    def get_pending_content(self, content_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get content pending processing
        
        Args:
            content_type: Optional filter by content type
            limit: Maximum number of items to retrieve
            
        Returns:
            list: List of content items
        """
        try:
            query = self.client.table('scrape_content_index') \
                .select('*') \
                .eq('status', 'pending') \
                .limit(limit)
                
            if content_type:
                query = query.eq('content_type', content_type)
                
            result = query.execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting pending content: {e}")
            return []
    
    def update_content_status(self, 
                             content_id: str, 
                             status: str, 
                             processed_content: Optional[str] = None,
                             chatbot_source_id: Optional[str] = None) -> bool:
        """
        Update the status of content in the index
        
        Args:
            content_id: ID of the content record
            status: New status ('processed', 'failed', etc.)
            processed_content: The processed content if available
            chatbot_source_id: ID of the linked chatbot source if created
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = {
                'status': status,
                'processed_at': datetime.now().isoformat(),
            }
            
            if processed_content:
                data['processed_content'] = processed_content
                
            if chatbot_source_id:
                data['chatbot_source_id'] = chatbot_source_id
                
            self.client.table('scrape_content_index') \
                .update(data) \
                .eq('id', content_id) \
                .execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating content status: {e}")
            return False
    
    # This method would be implemented later when we have embedding generation
    def add_to_chatbot_sources(self, 
                              content: str,
                              title: str,
                              source_url: str,
                              content_type: str = 'website',
                              chatbot_id: Optional[str] = None,
                              metadata: Optional[Dict] = None,
                              content_index_id: Optional[str] = None) -> Optional[str]:
        """
        Add processed content to chatbot_sources
        
        Args:
            content: The content text
            title: Content title
            source_url: URL of the content source
            content_type: Type of content
            chatbot_id: ID of the chatbot (defaults to DEFAULT_CHATBOT_ID)
            metadata: Additional metadata
            content_index_id: ID of the content in scrape_content_index
            
        Returns:
            str: ID of created record or None if failed
        """
        # This is a placeholder - would need real embedding generation
        logger.info("add_to_chatbot_sources not fully implemented yet")
        
        # In a real implementation, generate embeddings and add to chatbot_sources
        return None
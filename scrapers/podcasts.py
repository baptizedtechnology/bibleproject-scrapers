import logging
from typing import List, Dict, Optional
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import re

from .base import BaseScraper

logger = logging.getLogger(__name__)

class PodcastScraper(BaseScraper):
    """Scraper for Bible Project podcasts"""
    
    def __init__(self, full_scrape: bool = False):
        super().__init__("podcasts")
        self.base_url = "https://bibleproject.com/podcasts/the-bible-project-podcast/"
        self.driver = None
        self.full_scrape = full_scrape
        
    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--window-size=1920,1080')  # Set a standard window size
        self.driver = webdriver.Chrome(options=options)
        
    def _scroll_to_element(self, element):
        """Scroll an element into view"""
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)  # Wait for scroll to complete
        
    def _load_podcasts(self) -> List[Dict]:
        """Load podcasts based on scrape mode"""
        self._init_driver()
        self.driver.get(self.base_url)
        
        if self.full_scrape:
            return self._load_all_podcasts()
        else:
            return self._get_podcast_links()
        
    def _load_all_podcasts(self) -> List[Dict]:
        """Load all podcasts by clicking the 'Load more' button until no more podcasts"""
        podcasts = []
        wait = WebDriverWait(self.driver, 10)
        max_attempts = 100  # Prevent infinite loops
        
        for attempt in range(max_attempts):
            try:
                # Wait for and find the "Load more" button
                load_more_button = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.button[data-appearance='secondary']"))
                )
                
                # Scroll the button into view
                self._scroll_to_element(load_more_button)
                
                # Try to click the button
                try:
                    load_more_button.click()
                except:
                    # If direct click fails, try using JavaScript
                    self.driver.execute_script("arguments[0].click();", load_more_button)
                
                logger.info("Clicked 'Load more' button")
                time.sleep(2)  # Wait for content to load
                
                # Get current podcast count
                current_podcasts = self._get_podcast_links()
                if len(current_podcasts) == len(podcasts):
                    logger.info("No new podcasts loaded, stopping")
                    break
                    
                podcasts = current_podcasts
                logger.info(f"Loaded {len(podcasts)} podcasts so far")
                
            except Exception as e:
                logger.info(f"Finished loading podcasts: {e}")
                break
                
        return podcasts
    
    def _get_podcast_links(self) -> List[Dict]:
        """Extract podcast links and titles from the current page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        podcast_blocks = soup.find_all('div', class_='podcast-episode-block')
        
        podcasts = []
        for block in podcast_blocks:
            # Get the link and title
            link_elem = block.find('a', class_='podcast-episode-block-image')
            title_elem = block.find('a', class_='podcast-episode-block-title')
            
            if link_elem and title_elem:
                href = link_elem.get('href')
                title = title_elem.find('span', class_='truncate').text.strip()
                
                # Get episode number and duration from meta data
                meta_data = block.find('div', class_='podcast-episode-block-meta')
                episode_number = None
                duration = None
                
                if meta_data:
                    # Extract episode number
                    episode_text = meta_data.find('span', class_='meta-data-list-item', string=re.compile(r'Episode \d+'))
                    if episode_text:
                        episode_number = episode_text.text.strip()
                    
                    # Extract duration
                    duration_elem = block.find('div', class_='podcast-episode-block-footer')
                    if duration_elem:
                        duration_text = duration_elem.find('div', class_='text').text.strip()
                        duration = duration_text
                
                # Make the URL absolute
                if not href.startswith('http'):
                    href = f"https://bibleproject.com{href}"
                    
                podcasts.append({
                    'title': title,
                    'url': href,
                    'episode_number': episode_number,
                    'duration': duration
                })
                
        return podcasts
    
    def _get_download_url(self, podcast_url: str) -> Optional[str]:
        """Get the download URL from a podcast page"""
        self.driver.get(podcast_url)
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Wait for and find the download button
            download_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.button[download]"))
            )
            return download_button.get_attribute('href')
        except Exception as e:
            logger.error(f"Failed to get download URL for {podcast_url}: {e}")
            return None
    
    def _store_podcast(self, podcast: Dict, download_url: str) -> bool:
        """Store podcast information in Supabase"""
        metadata = {
            'episode_number': podcast['episode_number'],
            'episode_title': podcast['title'],
            'timestamp': None,  # Will be added during chunking
            'duration': podcast['duration']
        }
        
        return self.add_content(
            download_url=download_url,
            content="",  # Empty content since we'll process audio later
            title=podcast['title'],
            status='new',
            content_type="podcast",
            metadata=metadata,
            source_url=podcast['url']
        )
    
    def scrape(self) -> bool:
        """Main scraping method"""
        try:
            # Load podcasts based on mode
            podcasts = self._load_podcasts()
            
            if not podcasts:
                logger.error("No podcasts found")
                return False
            
            # Log the number of podcasts found
            logger.info(f"Found {len(podcasts)} podcasts to process")
            
            # Store each podcast in Supabase
            for podcast in podcasts:
                logger.info(f"Processing podcast: {podcast['title']}")
                
                # Get download URL
                download_url = self._get_download_url(podcast['url'])
                if not download_url:
                    logger.error(f"Failed to get download URL for podcast: {podcast['title']}")
                    continue
                
                # Store in Supabase
                if self._store_podcast(podcast, download_url):
                    logger.info(f"Successfully stored podcast: {podcast['title']}")
                else:
                    logger.info(f"Podcast already exists or failed to store: {podcast['title']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during podcast scraping: {e}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()

import logging
import re
from bs4 import BeautifulSoup
from pathlib import Path

from scrapers.base import BaseScraper
from utils.helpers import extract_text_from_pdf, extract_metadata_from_filename, clean_filename

logger = logging.getLogger(__name__)

class StudyNotesScraper(BaseScraper):
    """Scraper for BibleProject study notes"""
    
    def __init__(self):
        super().__init__(name="Study_Notes")
        self.study_notes_url = "https://bibleproject.com/downloads/study-notes/"
    
    def scrape(self) -> bool:
        """
        Scrape BibleProject study notes
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            logger.info(f"Starting to scrape BibleProject study notes from {self.study_notes_url}")
            
            # Get the main download page
            response = self.make_request(self.study_notes_url)
            if not response:
                logger.error("Failed to load study notes page")
                return False
            
            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all download cards
            download_cards = soup.select('div.download-bundles-card-image')
            logger.info(f"Found {len(download_cards)} study note download cards")
            self.items_found = len(download_cards)
            
            # Process each download card
            for card in download_cards:
                try:
                    # Find the parent element with the link
                    link_element = card.find_parent('a')
                    if not link_element:
                        logger.warning("Could not find download link for a study note card")
                        continue
                    
                    # Get the download link
                    resource_link = link_element.get('href')
                    if not resource_link:
                        continue
                    
                    # Make sure the link is absolute
                    if not resource_link.startswith('http'):
                        resource_link = f"https://bibleproject.com{resource_link}"
                    
                    # Get the resource title from the card if available
                    title_element = card.find_next('div', class_='download-bundles-card-title')
                    title = title_element.text.strip() if title_element else "Study Notes"
                    
                    logger.info(f"Processing study note: {title} ({resource_link})")
                    
                    # Get the resource page
                    self._process_resource_page(resource_link, title)
                    
                except Exception as e:
                    logger.exception(f"Error processing resource card: {e}")
            
            # Record scraping results
            self.record_scrape_results()
            logger.info(f"Completed scraping study notes. Found: {self.items_found}, New: {self.items_new}")
            return True
            
        except Exception as e:
            logger.exception(f"Error scraping study notes: {e}")
            self.record_scrape_results(status='failed', error=str(e))
            return False
    
    def _process_resource_page(self, resource_url, title):
        """Process a resource page to get the PDF download link"""
        
        response = self.make_request(resource_url)
        if not response:
            logger.warning(f"Failed to load resource page: {resource_url}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the download button
        download_btn = soup.select_one('a.resource-popout-button')
        if not download_btn:
            logger.warning(f"Could not find download button on page: {resource_url}")
            return
        
        # Get the download link
        download_link = download_btn.get('href')
        if not download_link:
            logger.warning(f"No download link found in button: {resource_url}")
            return
        
        # Make sure the link is absolute
        if not download_link.startswith('http'):
            download_link = f"https://bibleproject.com{download_link}"
        
        # Extract the PDF file name from the URL
        pdf_name = download_link.split('/')[-1]
        if not pdf_name or not pdf_name.lower().endswith('.pdf'):
            pdf_name = f"{clean_filename(title)}.pdf"
        
        # Download the PDF
        pdf_path = self.download_file(download_link, pdf_name)
        if not pdf_path:
            logger.warning(f"Failed to download PDF: {download_link}")
            return
        
        # Process the PDF content
        self._process_pdf(pdf_path, title, resource_url)
    
    def _process_pdf(self, pdf_path: Path, title: str, source_url: str):
        """Process a downloaded PDF file"""
        print("Reached _process_pdf")
        
        # try:
        #     # Extract text from PDF
        #     pdf_text = extract_text_from_pdf(pdf_path)
            
        #     if not pdf_text:
        #         logger.warning(f"Could not extract text from PDF: {pdf_path}")
        #         return
            
        #     # Get metadata from filename
        #     metadata = extract_metadata_from_filename(pdf_path.name)
            
        #     # Add source info to metadata
        #     metadata.update({
        #         'title': title,
        #         'source_url': source_url,
        #         'file_path': str(pdf_path),
        #         'file_size': pdf_path.stat().st_size,
        #         'scraper': self.name
        #     })
            
        #     # Add content to database
        #     added = self.add_content(
        #         url=source_url,
        #         content=pdf_text,
        #         title=title,
        #         content_type='study_notes',
        #         metadata=metadata
        #     )
            
        #     if added:
        #         logger.info(f"Added new study note: {title}")
        #     else:
        #         logger.info(f"Study note already exists: {title}")
                
        # except Exception as e:
        #     logger.exception(f"Error processing PDF {pdf_path}: {e}")
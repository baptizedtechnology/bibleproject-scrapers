import logging
import re
from bs4 import BeautifulSoup
from pathlib import Path
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
    

from scrapers.base import BaseScraper
from utils.helpers import extract_text_from_pdf, clean_filename, merge_metadata

logger = logging.getLogger(__name__)

#Required metadata for study_notes will be type article with format below.
CONTENT_TYPE = 'article'
#However, we can only fill in the author and publication date for now. Page will be filled during chunking.
'''
{
    "page": 5,
    "author": "Sarah Johnson",
    "publication_date": "2024-05-20"
}
'''

class StudyNotesScraper(BaseScraper):
    """Scraper for BibleProject study notes"""
    
    def __init__(self):
        super().__init__(name="Study_Notes")
        self.study_notes_url = "https://bibleproject.com/downloads/study-notes/"
        self.source_type = CONTENT_TYPE
        
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
            
            # Find all download bundle cards (parent containers)
            download_bundle_cards = soup.select('div.download-bundles-card')
            logger.info(f"Found {len(download_bundle_cards)} study note download cards")
            self.items_found = len(download_bundle_cards)
            
            # Process each download card
            for card in download_bundle_cards:
                try:
                    # Extract the resource ID
                    resource_id = card.get('data-popout-resource-id')
                    if not resource_id:
                        logger.warning("Could not find resource ID in card")
                        continue
                    
                    # Find the title element
                    title_element = card.select_one('div.download-bundles-card-title')
                    title = title_element.text.strip() if title_element else "Study Notes"
                    
                    logger.info(f"Processing study note: {title} (ID: {resource_id})")
                    
                    # Get the download link directly from the popout
                    download_url = f"https://bibleproject.com/view-resource/{resource_id}/"
                    
                    # Process the download link
                    self._process_download_link(download_url, title)
                    
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
        
    def _process_download_link(self, download_url, title):
        """Process a download link to get the PDF using headless browser"""
        
        logger.info(f"Processing download link: {download_url} for {title}")
        
        try:
            # Get PDF URL using headless browser
            pdf_url = self._get_pdf_url_with_selenium(download_url)
            
            if not pdf_url:
                logger.error(f"Failed to get PDF URL for {title}")
                return
                
            logger.info(f"Found PDF URL: {pdf_url}")
            
            # Extract the filename from the URL
            pdf_name = pdf_url.split('/')[-1]
            if not pdf_name or not pdf_name.lower().endswith('.pdf'):
                pdf_name = f"{clean_filename(title)}.pdf"
            
            # Download the PDF
            pdf_path = self.download_file(pdf_url, pdf_name)
            if not pdf_path:
                logger.warning(f"Failed to download PDF from: {pdf_url}")
                return
            
            # Process the PDF content
            self._process_pdf(pdf_path, title, pdf_url)
            
        except Exception as e:
            logger.exception(f"Error processing download link {download_url}: {e}")

    def _get_pdf_url_with_selenium(self, url):
        """
        Get the final PDF URL using Selenium headless browser
        
        Args:
            url: The initial URL to navigate to
            
        Returns:
            str: The final PDF URL or None if not found
        """
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        logger.info(f"Getting PDF URL with headless browser: {url}")
        
        try:
            # Set up Chrome options
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=options)
            
            # Navigate to URL
            driver.get(url)
            
            # Wait for redirects to complete
            time.sleep(3)  # Adjust timing based on site behavior
            
            # Get the final URL
            final_url = driver.current_url
            
            # Check if we've reached a PDF URL
            if final_url.lower().endswith('.pdf'):
                return final_url
            
            # If not a PDF URL directly, check if there's a PDF viewer
            if 'pdf' in final_url.lower() or 'view-resource' in final_url.lower():
                # Try to find PDF URL in page source
                page_source = driver.page_source
                
                # Look for cloudfront links which often host PDFs
                import re
                pdf_links = re.findall(r'https://[^"\']+\.pdf', page_source)
                
                if pdf_links:
                    return pdf_links[0]
            
            # Close the driver
            driver.quit()
            
            if not final_url.lower().endswith('.pdf'):
                logger.warning(f"Final URL is not a PDF: {final_url}")
                return None
                
            return final_url
            
        except Exception as e:
            logger.exception(f"Error getting PDF URL with Selenium: {e}")
            return None
            
        finally:
            # Make sure to quit the driver
            try:
                if 'driver' in locals():
                    driver.quit()
            except:
                pass
    
    def _process_pdf(self, pdf_path: Path, title: str, download_url: str):
        """Process a downloaded PDF file"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        try:
            # Extract text from PDF
            pdf_text = extract_text_from_pdf(pdf_path)
            
            if not pdf_text:
                logger.warning(f"Could not extract text from PDF: {pdf_path}")
                return
        

            base_metadata = {
                "author": "BibleProject",
                #NOTE: Cannot find publication date info. Will use past date for now.
                "publication_date": "2024-05-20",
            }

            extra_metadata = {
                "title": title,
                "download_url": download_url,
                "scraper": self.name,
            }

            # Merge metadata
            metadata = merge_metadata(
                base_metadata=base_metadata, 
                new_metadata=extra_metadata
            )
            
            # Add content to database
            added = self.add_content(
                download_url=download_url,
                content=pdf_text,
                title=title,
                content_type=CONTENT_TYPE,
                metadata=metadata
            )
            
            if added:
                logger.info(f"Added new study note: {title}")
            else:
                logger.info(f"Study note already exists: {title}")
                
        except Exception as e:
            logger.exception(f"Error processing PDF {pdf_path}: {e}")
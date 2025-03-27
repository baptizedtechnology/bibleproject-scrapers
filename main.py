import argparse
import logging
import sys
from datetime import datetime

# Import scrapers (to be implemented)
from scrapers.podcasts import PodcastScraper
# from scrapers.classroom import ClassroomScraper
from scrapers.study_notes import StudyNotesScraper
from utils.helpers import cleanup_temp_files

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"bibleproject_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)

def scrape_podcasts(full_scrape: bool = False):
    """
    Scrape BibleProject podcast content
    
    Args:
        full_scrape: If True, scrape all podcasts. If False, only check first 20 for new content.
    """
    logger.info(f"Starting podcast scraper in {'full' if full_scrape else 'new content'} mode")
    podcast_scraper = PodcastScraper(full_scrape=full_scrape)
    success = podcast_scraper.scrape()
    
    if success:
        logger.info(f"Podcast scraping completed successfully. Found {podcast_scraper.items_found} items, added {podcast_scraper.items_new} new items.")
    else:
        logger.error("Podcast scraping failed")

def scrape_classroom():
    """
    Scrape BibleProject classroom content
    """
    logger.info("Starting classroom scraper")
    # classroom_scraper = ClassroomScraper()
    # classroom_scraper.scrape()
    logger.info("Classroom scraping not yet implemented")

def scrape_study_notes():
    """
    Scrape BibleProject study notes
    """
    logger.info("Starting study notes scraper")
    study_notes_scraper = StudyNotesScraper()
    success = study_notes_scraper.scrape()
    if success:
        logger.info(f"Study notes scraping completed successfully. Found {study_notes_scraper.items_found} items, added {study_notes_scraper.items_new} new items.")
    else:
        logger.error("Study notes scraping failed")

def process_pending():
    """
    Process any pending content (transcribe audio, create embeddings)
    """
    logger.info("Processing pending content")
    from processors.runner import process_pending_content
    
    processed_count = process_pending_content()
    
    if processed_count > 0:
        logger.info(f"Successfully processed {processed_count} pending items")
    else:
        logger.info("No pending items processed")

def main():
    """Main entry point for the scraper"""
    parser = argparse.ArgumentParser(description='BibleProject content scraper')
    parser.add_argument('--podcasts', action='store_true', help='Scrape podcast content')
    parser.add_argument('--classroom', action='store_true', help='Scrape classroom content')
    parser.add_argument('--study-notes', action='store_true', help='Scrape study notes')
    parser.add_argument('--process', action='store_true', help='Process pending content')
    parser.add_argument('--full', action='store_true', help='Run full scrape (all content types)')
    parser.add_argument('--full-podcasts', action='store_true', help='Run full podcast scrape (all podcasts)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    try:
        # Determine what to run based on arguments
        if args.podcasts or args.full:
            scrape_podcasts(full_scrape=args.full_podcasts)
            
        if args.classroom or args.full:
            scrape_classroom()
            
        if args.study_notes or args.full:
            scrape_study_notes()
            
        if args.process or args.full:
            process_pending()
            
        logger.info("Scraping completed successfully")
        cleanup_temp_files()
        
    except Exception as e:
        logger.exception(f"Error during scraping: {e}")
        cleanup_temp_files()
        sys.exit(1)

if __name__ == "__main__":
    main()
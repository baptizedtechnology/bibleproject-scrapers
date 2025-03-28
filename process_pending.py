import logging
import sys
from processors.audio import AudioProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def process_pending():
    """Process pending podcasts"""
    # Initialize audio processor
    processor = AudioProcessor(content_type='podcast')
    
    logger.info("Starting to process pending podcasts...")
    
    # Process pending podcasts (limit of 40)
    processed_count = processor.process_pending_podcasts(limit=None)
    
    logger.info(f"Processed {processed_count} pending podcasts")

if __name__ == "__main__":
    process_pending() 
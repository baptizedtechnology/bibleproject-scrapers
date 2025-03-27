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

def test_chunk_podcast():
    """Test chunking a specific podcast"""
    # Initialize audio processor
    processor = AudioProcessor()
    
    # Test podcast ID
    podcast_id = "a0cc2471-bd81-4390-9350-f298295d50dd"
    
    logger.info(f"Testing chunking for podcast ID: {podcast_id}")
    
    # Process the podcast
    success = processor.chunk_podcast(podcast_id)
    
    if success:
        logger.info("Successfully chunked podcast")
    else:
        logger.error("Failed to chunk podcast")

if __name__ == "__main__":
    test_chunk_podcast() 
import logging
from pathlib import Path
from processors.audio import AudioProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_audio_processor():
    """Test the audio processor with a single podcast"""
    # Initialize processor
    processor = AudioProcessor()
    
    # Test URL - replace with an actual podcast URL from your database
    test_url = "https://afp-597195-injected.calisto.simplecastaudio.com/695767b0-cd40-4e6c-ac8c-ac6bc0df77ee/episodes/1f3ffdd7-b6b6-480b-ba9f-be4c4a069f2c/audio/128/default.mp3?awCollectionId=695767b0-cd40-4e6c-ac8c-ac6bc0df77ee&awEpisodeId=1f3ffdd7-b6b6-480b-ba9f-be4c4a069f2c"
    
    logger.info("Starting audio processing test")
    
    # Process the audio
    result = processor.process_audio(test_url)
    
    if result:
        logger.info("Successfully processed audio file")
        logger.info(f"Transcription saved to: {processor.temp_dir}")
    else:
        logger.error("Failed to process audio file")

if __name__ == "__main__":
    test_audio_processor() 
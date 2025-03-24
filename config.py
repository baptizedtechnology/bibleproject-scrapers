import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# BibleProject site URLs
BP_BASE_URL = "https://bibleproject.com"
BP_PODCAST_URL = f"{BP_BASE_URL}/podcasts/the-bible-project-podcast/"
#FIXME: it'll be more complicated than this
BP_CLASSROOM_URL = f"{BP_BASE_URL}/classroom"
#FIXME: study notes diff than this
BP_STUDY_NOTES_URL = f"{BP_BASE_URL}/explore"

# Request settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', '1.0'))  # Delay between requests in seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # Request timeout in seconds

# Chatbot configuration
DEFAULT_CHATBOT_ID = os.getenv('DEFAULT_CHATBOT_ID')
DEFAULT_CONTENT_TYPE = "website" 

# Audio processing
SPEECH_TO_TEXT_API = os.getenv('SPEECH_TO_TEXT_API', 'openai')  # 'openai', 'google', 'azure'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'whisper-1')

# Processing settings
MAX_CONTENT_CHUNK_SIZE = int(os.getenv('MAX_CONTENT_CHUNK_SIZE', '4000'))  # Characters per chunk
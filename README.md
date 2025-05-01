# Bible Project Content Scraper

A collection of scrapers and processors for Bible Project content, designed to create a comprehensive knowledge base for AI chatbots.

## Project Status

May 1, 2025
- Stopped the scraper for now. Plenty of similar tools to this out in the world, so I'll likely spend time working with others.

As of March 28, 2025:
- 60 podcasts are currently transcribed and chunked in the database
- Monthly processing of 40 additional podcasts (to manage Whisper API costs)
- Classroom content scraping planned for future implementation

## Project Structure

```
bibleproject-scrapers/
├── .github/
│   └── workflows/              # GitHub Actions workflows
│       ├── run_scraper.yml     # Podcast scraping workflow
│       └── run_study_notes.yml # Study notes scraping workflow
├── scrapers/                   # Content scrapers
│   ├── base.py                # Base scraper class
│   ├── podcasts.py            # Podcast scraper
│   └── study_notes.py         # Study notes scraper
├── processors/                 # Content processors
│   ├── audio.py               # Audio transcription
│   ├── text.py                # Text processing
│   └── runner.py              # Processor orchestration
├── db/                        # Database operations
│   └── supabase.py           # Supabase client
├── utils/                     # Utility functions
│   └── helpers.py            # Helper functions
├── main.py                    # Main entry point
├── config.py                  # Configuration
└── requirements.txt           # Dependencies
```

## Setup

1. Clone the repository:
```bash
git clone https://github.com/baptizedtechnology/bibleproject-scrapers
cd bibleproject-scrapers
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DEFAULT_CHATBOT_ID=your_chatbot_id #This is a key for Supabase to link the source to the right chatbot
```

## Usage

### Main Commands

- Scrape podcasts:
```bash
python main.py --podcasts
```

- Process content:
```bash
#See main.py for all options, but typically we run a scraper like this:
python main.py --process --content-type [podcast|study_notes|classroom] --limit [number]
```

### Monthly Processing

The project uses GitHub Actions to:
1. Scrape new content on the 1st of each month
2. Process up to 40 pending podcasts
3. Process study notes
4. Store results in Supabase

## Contributing

### Creating New Scrapers

1. Copy an existing scraper from `/scrapers` as a template
2. Modify the scraper for your content type
3. Use the helper functions in `utils/helpers.py` to ensure proper data formatting
4. Add your scraper to `main.py`

### Helper Functions

The project includes several helper functions to standardize data:
- `clean_filename()`: Sanitize filenames
- `extract_text_from_pdf()`: Extract text from PDFs
- `split_text_into_chunks()`: Split text into manageable chunks
- `create_embedding()`: Generate embeddings for content

### Database Schema

Content is stored in two main tables:
1. `scrape_content_index`: Raw content with metadata
2. `chatbot_sources`: Processed and chunked content ready for chatbot use

## Development

### Adding New Content Types

1. Create a new scraper in `/scrapers`
2. Create a new processor in `/processors` if needed
3. Update `processors/runner.py` to handle the new content type
4. Add appropriate GitHub Actions workflow

### Testing

Test scripts are available in the root directory:
- `test_audio.py`: Test audio processing
- `test_chunk.py`: Test content chunking
- `process_pending.py`: Process pending content

## License

MIT

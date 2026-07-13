# bluk-cf

Python automation project for email generation, signup flows, and token validation.

## Project Structure

- `main.py` - Main entry point
- `src/` - Core modules
  - `email_generator.py` - Email generation
  - `email_verifier.py` - Email verification
  - `signup_flow.py` - Signup automation
  - `token_creator.py` - Token creation
  - `token_validator.py` - Token validation
  - `turnstile_bypass.py` - Turnstile handling
  - `live_dashboard.py` - Live dashboard
  - `utils.py` - Utilities
- `scripts/` - Utility scripts
  - `add_to_9router.py` - 9router integration
  - `export_9router_txt.py` - 9router export
- `tests/` - Test suite

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run main application
python main.py

# Run tests
pytest tests/

# Run specific script
python scripts/add_to_9router.py
python scripts/export_9router_txt.py

# Run dashboard
python src/live_dashboard.py
```

## Stack

- **Runtime**: Python 3.x
- **Web automation**: nodriver, playwright
- **Image processing**: opencv-python-headless, Pillow
- **HTTP client**: httpx
- **CLI**: rich

## Development

This project uses web automation tools. Browser drivers are managed by nodriver and playwright.

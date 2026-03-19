from unittest.mock import patch
import os

with patch.dict(os.environ, {}, clear=True):
    print("Environ:", os.environ)
    import dotenv
    # by default load_dotenv searches for .env
    dotenv.load_dotenv()
    print("Environ after:", os.environ)
    DATABASE_URL = os.environ.get("DATABASE_URL")
    print("DB URL:", DATABASE_URL)

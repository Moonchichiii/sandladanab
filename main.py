"""Entry point. Run: uvicorn main:app --reload"""

from app import create_app

app = create_app()
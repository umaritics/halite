import os
from config import settings
from services.groq_service import GroqService

groq = GroqService(api_key=settings.GROQ_API_KEY, demo_mode=settings.DEMO_MODE)
print(f"Groq is_live: {groq.is_live}")
print(f"Groq demo_mode: {groq.demo_mode}")
if hasattr(groq, "client"):
    print(f"Groq client: {groq.client}")

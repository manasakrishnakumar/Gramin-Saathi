from sarvamai import SarvamAI
from app.core.config import settings


class SarvamTranslationService:
    def __init__(self):
        if settings.SARVAM_API_KEY:
            self.client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)
        else:
            self.client = None

    def translate_to_english(self, text: str, source_language: str):
        if not self.client:
            raise Exception("SARVAM_API_KEY not configured")
        """
        Translate text to English if source language is not English.
        """

        # If already English, skip translation
        if source_language == "en-IN":
            return text

        response = self.client.text.translate(
            input=text,
            source_language_code=source_language,
            target_language_code="en-IN"
        )

        return response.translated_text

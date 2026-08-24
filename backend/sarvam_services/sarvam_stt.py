from sarvamai import SarvamAI
from app.core.config import settings

class SarvamSTTService:
    def __init__(self):
        if settings.SARVAM_API_KEY:
            self.client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)
        else:
            self.client = None

    def transcribe_file(self, file_path: str, language_code="unknown"):
        """
        Transcribe an audio file using Sarvam STT.
        Returns the full response object which includes:
        - transcript: The transcribed text
        - language_code: The detected language (e.g., "kn-IN" for Kannada)
        """
        if not self.client:
            raise Exception("SARVAM_API_KEY not configured")
        
        with open(file_path, "rb") as audio_file:
            response = self.client.speech_to_text.transcribe(
                file=audio_file,
                language_code=language_code,
                model="saarika:v2.5"
            )
        
        # Debug: Print the full response to see available fields
        print(f"[STT DEBUG] Full response type: {type(response)}")
        print(f"[STT DEBUG] Transcript: {response.transcript if hasattr(response, 'transcript') else 'N/A'}")
        print(f"[STT DEBUG] Language code: {response.language_code if hasattr(response, 'language_code') else 'N/A'}")
        
        # Print all attributes of response for debugging
        if hasattr(response, '__dict__'):
            print(f"[STT DEBUG] Response attributes: {response.__dict__}")
        
        return response

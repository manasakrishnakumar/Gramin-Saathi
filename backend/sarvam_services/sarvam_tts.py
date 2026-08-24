from sarvamai import SarvamAI
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

# Sarvam TTS has a text length limit (approximately 500 chars per request)
MAX_TTS_TEXT_LENGTH = 500

# Unicode ranges for Indian scripts
SCRIPT_RANGES = {
    "kn-IN": ("\u0C80", "\u0CFF"),  # Kannada
    "hi-IN": ("\u0900", "\u097F"),  # Devanagari (Hindi)
    "ta-IN": ("\u0B80", "\u0BFF"),  # Tamil
    "te-IN": ("\u0C00", "\u0C7F"),  # Telugu
    "ml-IN": ("\u0D00", "\u0D7F"),  # Malayalam
    "gu-IN": ("\u0A80", "\u0AFF"),  # Gujarati
    "bn-IN": ("\u0980", "\u09FF"),  # Bengali
    "mr-IN": ("\u0900", "\u097F"),  # Marathi (uses Devanagari)
    "pa-IN": ("\u0A00", "\u0A7F"),  # Punjabi (Gurmukhi)
    "or-IN": ("\u0B00", "\u0B7F"),  # Odia
}


class SarvamTTSService:
    def __init__(self):
        if settings.SARVAM_API_KEY:
            self.client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)
        else:
            self.client = None

    def _extract_native_text(self, text: str, language_code: str) -> str:
        """
        Extract only the native language portion from mixed text.
        For non-English languages, find and return only the native script portion.
        """
        if language_code == "en-IN":
            return text
        
        script_range = SCRIPT_RANGES.get(language_code)
        if not script_range:
            return text
        
        start, end = script_range
        
        # Find portions containing native script
        native_portions = []
        current_portion = []
        in_native = False
        
        for char in text:
            is_native = start <= char <= end or char in ' .,!?।॥\n'
            
            if is_native:
                current_portion.append(char)
                in_native = True
            elif in_native and current_portion:
                # End of native portion
                portion = ''.join(current_portion).strip()
                if len(portion) > 10:  # Only keep meaningful portions
                    native_portions.append(portion)
                current_portion = []
                in_native = False
        
        # Don't forget the last portion
        if current_portion:
            portion = ''.join(current_portion).strip()
            if len(portion) > 10:
                native_portions.append(portion)
        
        if native_portions:
            result = ' '.join(native_portions)
            print(f"[TTS DEBUG] Extracted native text: {result[:100]}...")
            return result
        
        # Fallback to original text if no native portions found
        return text

    def synthesize_speech(self, text: str, language_code: str):
        if not self.client:
            raise Exception("SARVAM_API_KEY not configured")
        
        # For non-English, extract only native language portion
        if language_code != "en-IN":
            text = self._extract_native_text(text, language_code)
        
        # Truncate text if too long for TTS
        original_length = len(text)
        if len(text) > MAX_TTS_TEXT_LENGTH:
            # Try to truncate at a sentence boundary
            truncated = text[:MAX_TTS_TEXT_LENGTH]
            last_period = truncated.rfind('.')
            # Also check for Kannada/Hindi sentence enders
            last_danda = max(truncated.rfind('।'), truncated.rfind('॥'))
            last_end = max(last_period, last_danda)
            
            if last_end > MAX_TTS_TEXT_LENGTH // 2:
                text = truncated[:last_end + 1]
            else:
                text = truncated + "..."
            print(f"TTS text truncated from {original_length} to {len(text)} chars")
        
        print(f"[TTS DEBUG] Final TTS text ({language_code}): {text[:200]}...")
        
        response = self.client.text_to_speech.convert(
            text=text,
            target_language_code=language_code,
            speaker="anushka",
            pitch=0,
            pace=1,
            loudness=1,
            speech_sample_rate=22050,
            enable_preprocessing=True,
            model="bulbul:v2"
        )
        
        if response.audios and len(response.audios) > 0:
            print(f"[TTS DEBUG] Audio generated, length: {len(response.audios[0])} chars")
            return response.audios[0]
        else:
            logger.error("TTS response has no audio data")
            raise Exception("TTS returned no audio")


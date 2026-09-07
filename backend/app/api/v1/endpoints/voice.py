from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import shutil
import os
import tempfile
import io
import base64

# Add parent directory to path to find sarvam-services if needed, 
# or assuming we can import since it's in backend root (might need empty __init__.py)
import sys
from pathlib import Path

# Adjust path to include backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))

from sarvam_services.sarvam_stt import SarvamSTTService
from sarvam_services.sarvam_tts import SarvamTTSService
from sarvam_services.sarvam_translate import SarvamTranslationService

router = APIRouter()
stt_service = SarvamSTTService()
tts_service = SarvamTTSService()
translate_service = SarvamTranslationService()

class TTSRequest(BaseModel):
    text: str
    language_code: str = "hi-IN" # Default Hindi

class TranslateRequest(BaseModel):
    text: str
    source_language: str

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language_code: str = Form("unknown")):
    """
    Convert audio file to text.
    """
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Transcribe
        response = stt_service.transcribe_file(tmp_path, language_code)
        
        # Cleanup
        os.remove(tmp_path)
        
        return {"transcript": response.transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech audio (base64 or blob).
    """
    try:
        # Returns raw audio bytes (or base64 depending on SDK)
        # Checking sarvam_tts.py: returns response.audios[0] which is base64 string usually?
        # The SDK doc says audios is list of base64 encoded strings
        audio_base64 = tts_service.synthesize_speech(request.text, request.language_code)
        
        # We can return base64 directly or stream it
        return {"audio": audio_base64, "encoding": "base64"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate")
async def translate(request: TranslateRequest):
    """
    Translate text to English.
    """
    try:
        translated = translate_service.translate_to_english(request.text, request.source_language)
        return {"translated_text": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/converse")
async def converse(file: UploadFile = File(...), language_code: str = Form("unknown")):
    """
    Full Voice Loop: Audio -> STT -> RAG (Logic) -> TTS -> Audio
    Supports bilingual response based on detected language.
    """
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    # Language mapping for Sarvam services
    SARVAM_LANGUAGE_MAP = {
        "hi": "hi-IN",  # Hindi
        "en": "en-IN",  # English
        "ta": "ta-IN",  # Tamil
        "te": "te-IN",  # Telugu
        "kn": "kn-IN",  # Kannada
        "ml": "ml-IN",  # Malayalam
        "mr": "mr-IN",  # Marathi
        "gu": "gu-IN",  # Gujarati
        "bn": "bn-IN",  # Bengali
        "pa": "pa-IN",  # Punjabi
        "or": "or-IN",  # Odia
    }
    
    LANGUAGE_NAMES = {
        "hi": "Hindi", "en": "English", "ta": "Tamil", "te": "Telugu",
        "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "gu": "Gujarati",
        "bn": "Bengali", "pa": "Punjabi", "or": "Odia"
    }
    
    # Import singleton here to avoid circular imports
    from app.services.rag_service import rag_service
    
    # 1. STT - Get transcript and detected language
    detected_lang_code = "en"  # Default to English
    query_text = ""
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        logger.info(f"Transcribing audio file: {tmp_path}")
        stt_resp = stt_service.transcribe_file(tmp_path, language_code)
        query_text = stt_resp.transcript
        
        # Extract detected language from STT response
        if hasattr(stt_resp, 'language_code') and stt_resp.language_code:
            detected_lang_code = stt_resp.language_code.split('-')[0]  # "hi-IN" -> "hi"
        elif hasattr(stt_resp, 'language') and stt_resp.language:
            detected_lang_code = stt_resp.language.split('-')[0]
        
        logger.info(f"STT Result: {query_text}, Detected Language: {detected_lang_code}")
        os.remove(tmp_path)
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Could not understand audio")
            
    except Exception as e:
        logger.error(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=f"STT Error: {e}")

    # 1b. Voice transcription quality check (trained classifier) — informational
    # flag only, never blocks the flow. Only meaningful for English text (the
    # classifier's reference vocabulary is English) — see
    # ml_voice_quality_service.py's documented false-positive limitation.
    voice_quality = None
    if detected_lang_code == "en":
        try:
            from app.services.ml_voice_quality_service import ml_voice_quality_service
            voice_quality = ml_voice_quality_service.check(query_text)
        except Exception as e:
            logger.warning(f"Voice quality check failed: {e}")

    # 2. RAG - Get response with bilingual translation
    response_text = ""
    target_language = LANGUAGE_NAMES.get(detected_lang_code, "Hindi")
    
    try:
        # Pass detected language to RAG for bilingual response
        stream_gen = rag_service.stream_query(query_text, target_language=target_language)
        
        for chunk_str in stream_gen:
            try:
                if not chunk_str.strip(): continue
                data = json.loads(chunk_str)
                if data.get("type") == "token":
                    response_text += data.get("content", "")
            except json.JSONDecodeError:
                pass
        
        logger.info(f"RAG Response length: {len(response_text)} chars")
                
    except Exception as e:
        logger.error(f"RAG Error: {e}")
        raise HTTPException(status_code=500, detail=f"RAG Error: {e}")

    if not response_text:
        response_text = "I'm sorry, I couldn't generate a response."

    # 3. TTS - Generate BILINGUAL audio (English + Native Language)
    try:
        native_lang_code = SARVAM_LANGUAGE_MAP.get(detected_lang_code, None)
        print(f"[TTS DEBUG] Detected lang: {detected_lang_code}, Native TTS code: {native_lang_code}")
        
        # Split response into English and native portions
        def extract_portions(text, script_start, script_end):
            """Extract English and native script portions from mixed text."""
            english_chars = []
            native_chars = []
            
            for char in text:
                if script_start <= char <= script_end or char in '।॥':
                    native_chars.append(char)
                elif char.isascii() or char in ' .,!?:\n-':
                    english_chars.append(char)
                else:
                    # Unknown script, add to both as space
                    english_chars.append(' ')
                    native_chars.append(' ')
            
            english_text = ''.join(english_chars).strip()
            native_text = ''.join(native_chars).strip()
            
            # Clean up multiple spaces
            import re
            english_text = re.sub(r'\s+', ' ', english_text)
            native_text = re.sub(r'\s+', ' ', native_text)
            
            return english_text, native_text
        
        # Detect which script is present
        script_ranges = {
            "kn-IN": ("\u0C80", "\u0CFF"),  # Kannada
            "hi-IN": ("\u0900", "\u097F"),  # Hindi
            "ta-IN": ("\u0B80", "\u0BFF"),  # Tamil
            "te-IN": ("\u0C00", "\u0C7F"),  # Telugu
            "ml-IN": ("\u0D00", "\u0D7F"),  # Malayalam
        }
        
        detected_script = None
        for lang, (start, end) in script_ranges.items():
            if any(start <= c <= end for c in response_text):
                detected_script = lang
                break
        
        audio_base64 = None
        audio_native = None
        
        if detected_script and detected_script != "en-IN":
            # Extract English and native portions
            script_start, script_end = script_ranges[detected_script]
            english_text, native_text = extract_portions(response_text, script_start, script_end)
            
            print(f"[TTS DEBUG] English portion: {english_text[:100]}...")
            print(f"[TTS DEBUG] Native portion ({detected_script}): {native_text[:100]}...")
            
            # Generate English TTS
            if english_text and len(english_text) > 20:
                print(f"[TTS DEBUG] Generating English TTS...")
                try:
                    audio_base64 = tts_service.synthesize_speech(english_text, "en-IN")
                except Exception as e:
                    print(f"[TTS DEBUG] English TTS failed: {e}")
            
            # Generate Native language TTS
            if native_text and len(native_text) > 20:
                print(f"[TTS DEBUG] Generating {detected_script} TTS...")
                try:
                    audio_native = tts_service.synthesize_speech(native_text, detected_script)
                except Exception as e:
                    print(f"[TTS DEBUG] Native TTS failed: {e}")
        else:
            # Pure English response
            print(f"[TTS DEBUG] English-only response, generating en-IN TTS")
            audio_base64 = tts_service.synthesize_speech(response_text, "en-IN")
        
        return {
            "query": query_text,
            "response": response_text,
            "audio": audio_base64,  # English audio
            "audio_native": audio_native,  # Native language audio (if available)
            "encoding": "base64",
            "detected_language": detected_lang_code,
            "tts_language": detected_script or "en-IN",
            "voice_quality": voice_quality,
        }
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        print(f"[TTS DEBUG] TTS Error: {e}")
        # Fallback: Return text even if TTS fails
        return {
            "query": query_text,
            "response": response_text,
            "error": f"TTS Error: {e}",
            "detected_language": detected_lang_code,
            "voice_quality": voice_quality,
        }

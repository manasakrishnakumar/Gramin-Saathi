from services.sarvam_translate import SarvamTranslationService


class VoiceQueryPipeline:
    """
    Handles:
    STT output -> (optional) Translation -> English query for search
    """

    def __init__(self):
        self.translator = SarvamTranslationService()

    def prepare_search_query(self, transcript: str, language_code: str) -> str:
        """
        Converts multilingual STT output into an English query
        suitable for RAG / database search.
        """

        english_text = self.translator.translate_to_english(
            text=transcript,
            source_language=language_code
        )

        return english_text

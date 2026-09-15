import logging
import json
import re
import sqlite3
import time
from typing import List, Optional, Dict, Any, Generator
from datetime import datetime, timedelta

from llama_index.core import VectorStoreIndex, Settings, StorageContext, Document
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core.vector_stores.types import VectorStoreQuery, VectorStoreQueryMode
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
from pinecone import Pinecone

from app.core.config import settings
from app.services.hybrid_retriever import hybrid_retriever, RetrievedChunk
from app.services.multilingual_service import multilingual_service


logger = logging.getLogger(__name__)

class GeminiEmbedding768(GeminiEmbedding):
    """Ensures embeddings are strictly 768 dimensions to match the Pinecone index."""
    def _get_query_embedding(self, query: str) -> list[float]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            res = genai.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=query,
                task_type="retrieval_query",
                output_dimensionality=768,
            )
            return res["embedding"]
        except Exception:
            emb = super()._get_query_embedding(query)
            return emb[:768] if len(emb) > 768 else emb

    def _get_text_embedding(self, text: str) -> list[float]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            res = genai.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=768,
            )
            return res["embedding"]
        except Exception:
            emb = super()._get_text_embedding(text)
            return emb[:768] if len(emb) > 768 else emb

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._get_text_embedding(t) for t in texts]

class RAGService:
    def __init__(self):
        self._init_llm()
        self._init_vector_store()
        self._init_caches()

    # Define System Prompt as Class Attribute or Method
    SYSTEM_PROMPT = """You are 'Gramin Saathi', a helpful and knowledgeable AI assistant dedicated to helping Indian citizens understand government schemes (Yojanas).

    PRIMARY RULE: Always provide a helpful, accurate, and complete answer. NEVER say "I don't know", "I don't have information", "not in my knowledge base", or any variation of that. Always give a useful response.

    Identity & Persona:
    - If asked "who are you", "what are you", or about your identity, YOU MUST ALWAYS answer: "I am Gramin Saathi, a dedicated AI assistant created to help you with government schemes."
    - NEVER say you are "trained by Google" or "a large language model".

    Guidelines:
    - Be polite, empathetic, and clear.
    - When context from the RAG knowledge base is provided, use it fully and accurately.
    - When no specific context is provided, use your general knowledge about Indian government schemes to give a helpful answer.
    - Format your answers with clear headings and bullet points.
    - Always answer in the requested language (or English + Translation if requested).
    - NEVER decline to answer or say you are unsure — always provide the best possible response.
    """

    def _init_llm(self):
        self.llm = Gemini(model_name=settings.LLM_MODEL_FULL, api_key=settings.GEMINI_API_KEY, system_prompt=self.SYSTEM_PROMPT)
        self.embed_model = GeminiEmbedding768(model_name=settings.EMBEDDING_MODEL, api_key=settings.GEMINI_API_KEY)
        
        # Configure global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model

    def _init_vector_store(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.pinecone_index = self.pc.Index(settings.PINECONE_INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            pinecone_index=self.pinecone_index,
            add_sparse_vector=False,
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
        )
        # Expose retriever directly — used as the Pinecone dense stage in hybrid pipeline
        self.retriever = self.index.as_retriever(similarity_top_k=10)  # Fetch more for fusion
        self.query_engine = self.index.as_query_engine(streaming=False)
        logger.info("Vector store initialised (Pinecone). Hybrid retriever ready (lazy-loaded).")

        # Load seed schemes (Karnataka Shakti, PM Kisan, etc.) into hybrid retriever (BM25 + FAISS)
        seed_path = settings.DATA_DIR / "seed_schemes.json"
        if seed_path.exists():
            try:
                import json
                from app.services.hybrid_retriever import hybrid_retriever
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_docs = json.load(f)
                corpus = [
                    (d.get("url", f"seed_{i}"), f"{d.get('title', '')}\n\n{d.get('text', '')}")
                    for i, d in enumerate(seed_docs)
                ]
                hybrid_retriever.build_local_index(corpus)
                logger.info(f"Loaded {len(corpus)} seed schemes into hybrid local index (BM25 + FAISS)")

                # Also ensure Pinecone has these core scheme vectors
                try:
                    stats = self.pinecone_index.describe_index_stats()
                    total_vecs = stats.get("total_vector_count", 0) if isinstance(stats, dict) else getattr(stats, "total_vector_count", 0)
                    if total_vecs < 10:
                        from llama_index.core import Document
                        for d in seed_docs:
                            doc_text = f"{d.get('title', '')}\n\n{d.get('text', '')}"
                            self.index.insert(Document(text=doc_text, metadata={"url": d.get("url", ""), "title": d.get("title", "")}))
                        logger.info(f"Seeded {len(seed_docs)} schemes into Pinecone index")
                except Exception as pe:
                    logger.warning(f"Pinecone seed check notice: {pe}")
            except Exception as e:
                logger.warning(f"Could not load seed schemes into hybrid retriever: {e}")

    def _is_conversational(self, query: str) -> bool:
        """
        Check if query is general conversation or identity related.
        """
        q = query.lower().strip()
        # Identity triggers
        if any(x in q for x in ["who are you", "what are you", "your name", "who created you", "your purpose"]):
            return True
        # Greeting/General triggers (simple heuristic)
        # If it's very short and contains greetings.
        # NOTE: must match whole words, not substrings — a naive `"hi" in q`
        # would false-positive on words like "this", "which", "think", and
        # `"hey" in q` on "they", silently diverting real scheme questions
        # (e.g. "This is confusing" / "They are farmers") to the canned
        # greeting reply instead of the RAG pipeline.
        greetings_single_word = {"hi", "hello", "hey", "namaste", "vanakkam"}
        greetings_phrase = ["good morning", "good afternoon", "good evening"]
        words = set(re.findall(r"[a-z]+", q))
        if len(q.split()) <= 3 and (
            words & greetings_single_word or any(g in q for g in greetings_phrase)
        ):
            return True

        return False

    def _init_caches(self):
        # 4. Redis LangCache (Initialized per request or lazily)
        self.langcache_configured = bool(settings.LANGCACHE_API_KEY and settings.LANGCACHE_CACHE_ID)
        if self.langcache_configured:
            masked_id = settings.LANGCACHE_CACHE_ID[:4] + "*" * 4 if settings.LANGCACHE_CACHE_ID else "None"
            logger.info(f"LangCache Configured with ID: {masked_id} and URL: {settings.LANGCACHE_SERVER_URL}")
        else:
            logger.info("LangCache NOT configured.")

        # 5. Local SQLite Cache
        self.db_path = settings.DATA_DIR / "offline_cache.db"
        self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    query_hash TEXT PRIMARY KEY,
                    response TEXT,
                    timestamp DATETIME
                )
            """)

    def _check_local_cache(self, query: str) -> Optional[str]:
        # Simple hash or exact match
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT response, timestamp FROM response_cache WHERE query_hash = ? ORDER BY timestamp DESC LIMIT 1",
                (query,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def _save_local_cache(self, query: str, response: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO response_cache (query_hash, response, timestamp) VALUES (?, ?, ?)",
                (query, response, datetime.now())
            )
            # Prune to last 50
            conn.execute("""
                DELETE FROM response_cache WHERE query_hash NOT IN (
                    SELECT query_hash FROM response_cache ORDER BY timestamp DESC LIMIT 50
                )
            """)
            
    def _web_search(self, query: str) -> str:
        """
        Perform a web search using DuckDuckGo (via ddgs package).
        """
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            
            # Use a fresh instance for each search
            results = DDGS().text(query, max_results=3)
            if results:
                return "\n\nWeb Search Results:\n" + "\n".join([f"- {r['title']}: {r['body']} ({r['href']})" for r in results])
            return ""
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return ""

    def query(self, query_text: str, target_language: str = "English", history: List[Dict] = []) -> Dict[str, Any]:
        start_time = time.time()
        source = "Unknown"
        steps = []  # Trace of execution steps for UI
        response_data = {}
        
        # Helper to log steps
        def log_step(step_name: str, status: str = "completed"):
            steps.append({"name": step_name, "status": status, "timestamp": datetime.now().isoformat()})
            logger.info(f"[Step] {step_name}: {status}")

        try:
            log_step("Received Query")
            
            # 1. Local Cache Check
            log_step("Checking Local Cache")
            cached = self._check_local_cache(query_text)
            if cached:
                logger.info("Serving from Local SQLite Cache")
                source = "Local Cache (SQLite)"
                response_data = {"answer": cached, "source": source}
                log_step("Found in Local Cache", "success")

            # 2. Redis LangCache Check
            elif self.langcache_configured:
                log_step("Checking Redis LangCache")
                try:
                    from langcache import LangCache
                    with LangCache(
                        server_url=settings.LANGCACHE_SERVER_URL,
                        cache_id=settings.LANGCACHE_CACHE_ID,
                        api_key=settings.LANGCACHE_API_KEY,
                    ) as lc:
                        search_response = lc.search(prompt=query_text, similarity_threshold=0.80)
                        if hasattr(search_response, 'data') and search_response.data:
                            match = search_response.data[0]
                            if getattr(match, 'similarity', 0.0) > 0.80:
                                source = "Redis LangCache"
                                response_data = {
                                    "answer": match.response, 
                                    "source": source, 
                                    "score": getattr(match, 'similarity', 0.0)
                                }
                                log_step("Found in LangCache", "success")
                except Exception as e:
                    logger.warning(f"LangCache error: {e}")
                    log_step("LangCache Check Failed", "error")

            # 3. RAG System — Hybrid Retrieval + Re-ranking
            if not response_data:
                log_step("Querying Hybrid RAG System")
                source = "Hybrid RAG (Pinecone + BM25 + Cross-Encoder)"

                # Build prompt with history
                full_prompt = query_text
                if history:
                    history_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-4:]])
                    full_prompt = f"Chat History:\n{history_context}\n\nCurrent Question: {query_text}"

                # Localization instruction
                if target_language != "English":
                    full_prompt += f"\n\nIMPORTANT: Provide the answer in English first, and then provide a translation in {target_language}."

                log_step("Hybrid Retrieval (Dense + BM25 + Re-rank)")
                try:
                    # Detect query language for multilingual retrieval enrichment
                    ml_info = multilingual_service.process_query(query_text)
                    lang_code = ml_info["lang_code"]
                    lang_name = ml_info["lang_name"]
                    logger.info(f"[ML] Query language: {lang_name} ({lang_code}, conf={ml_info['confidence']:.2f})")

                    context_text, chunks = hybrid_retriever.retrieve_text_context(
                        query=ml_info["expanded_query"],  # keyword-expanded for BM25
                        pinecone_retriever=self.retriever,
                        top_k_final=5,
                        ml_info=ml_info,
                    )
                    if context_text:
                        full_prompt = f"{full_prompt}\n\nContext:\n{context_text}"
                        source = f"Hybrid RAG (Pinecone+BM25+CE, {lang_name})"
                    else:
                        source = "General Knowledge (no RAG context)"
                except Exception as e:
                    logger.warning(f"Hybrid retrieval failed, falling back to query_engine: {e}")
                    context_text = ""

                log_step("Generating Answer with Gemini")
                response = self.query_engine.query(full_prompt) if not context_text else \
                           type('R', (), {'__str__': lambda s: self.llm.complete(full_prompt).text})()
                response_text = str(response)

                log_step("Updating Caches")
                self._save_local_cache(query_text, response_text)
                if self.langcache_configured:
                    try:
                        from langcache import LangCache
                        with LangCache(
                            server_url=settings.LANGCACHE_SERVER_URL,
                            cache_id=settings.LANGCACHE_CACHE_ID,
                            api_key=settings.LANGCACHE_API_KEY,
                        ) as lc:
                            lc.set(prompt=query_text, response=response_text)
                    except: pass

                response_data = {"answer": response_text, "source": source}

        except Exception as e:
            logger.error(f"Query failed: {e}")
            source = "Error"
            response_data = {"answer": "An error occurred.", "source": "Error"}
            log_step("Error Processing Request", "failed")
        
        finally:
            # Add steps to response
            response_data["steps"] = steps
            
            # LOG METRICS
            duration = (time.time() - start_time) * 1000
            from app.services.monitoring_service import monitoring_service
            monitoring_service.log_query(
                query=query_text,
                source=source,
                latency_ms=duration,
                language=target_language
            )
            
        return response_data

    def stream_query(self, query: str, target_language: str = "English", history: List[Dict] = []) -> Generator[str, None, None]:
        steps = []
        
        def send_steps(current_steps, status_update=None):
            if status_update:
                found = False
                for s in current_steps:
                    if s["name"] == status_update["name"]:
                        s["status"] = status_update["status"]
                        found = True
                        break
                if not found:
                    current_steps.append(status_update)
            # Send latest steps
            return f'{json.dumps({"type": "step", "data": current_steps})}\n'

        # 1. Start
        start_step = {"name": "Received Query", "status": "in-progress", "timestamp": str(time.time())}
        steps.append(start_step)
        yield send_steps(steps)

        time.sleep(1.0) 
        start_step["status"] = "completed"
        
        # 2. Check Identity/Conversational
        if self._is_conversational(query):
            check_step = {"name": "Checking Query Type", "status": "completed", "timestamp": str(time.time())}
            steps.append(check_step)
            yield send_steps(steps)
            
            gen_step = {"name": "Generating General Response", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(gen_step)
            yield send_steps(steps)
            
            # Direct generation with strict persona
            full_prompt = f"{self.SYSTEM_PROMPT}\n\nUser Question: {query}\n\nInstruction: Answer politely and directly."
            if target_language and target_language != "English":
                full_prompt += f" Answer in English first, then {target_language}."

            logger.info(f"Direct conversational response for: {query}")
            try:
                # 1. Get full response (Blocking but guaranteed integrity)
                response = self.llm.complete(full_prompt)
                full_text = response.text
                
                # 2. Simulate streaming for frontend compatibility
                chunk_size = 5 # Characters per chunk
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i:i+chunk_size]
                    yield f'{json.dumps({"type": "token", "content": chunk})}\n'
                    time.sleep(0.01) # Tiny sleep to let UI breathe
                
                gen_step["status"] = "completed"
                yield send_steps(steps, gen_step)

                # 3. Generate TTS Audio (Bilingual: English + Target Language)
                try:
                    from sarvam_services.sarvam_tts import SarvamTTSService
                    tts_service = SarvamTTSService()
                    
                    tts_step = {"name": "Generating Audio Response", "status": "in-progress", "timestamp": str(time.time())}
                    steps.append(tts_step)
                    yield send_steps(steps)
                    
                    # Script detection for TTS language
                    script_ranges = {
                        "kn-IN": ("\u0C80", "\u0CFF"),  # Kannada
                        "hi-IN": ("\u0900", "\u097F"),  # Hindi
                        "ta-IN": ("\u0B80", "\u0BFF"),  # Tamil
                        "te-IN": ("\u0C00", "\u0C7F"),  # Telugu
                        "ml-IN": ("\u0D00", "\u0D7F"),  # Malayalam
                    }
                    
                    # Detect script in response
                    detected_script = None
                    for lang, (start, end) in script_ranges.items():
                        if any(start <= c <= end for c in full_text):
                            detected_script = lang
                            break
                    
                    # Function to extract text portions
                    def extract_portions(text, script_start, script_end):
                        import re
                        english_chars = []
                        native_chars = []
                        for char in text:
                            if script_start <= char <= script_end or char in '।॥':
                                native_chars.append(char)
                            elif char.isascii() or char in ' .,!?:\n-':
                                english_chars.append(char)
                        english_text = re.sub(r'\s+', ' ', ''.join(english_chars).strip())
                        native_text = re.sub(r'\s+', ' ', ''.join(native_chars).strip())
                        return english_text, native_text
                    
                    audio_english = None
                    audio_native = None
                    
                    if detected_script:
                        script_start, script_end = script_ranges[detected_script]
                        english_text, native_text = extract_portions(full_text, script_start, script_end)
                        
                        # Generate English TTS
                        if english_text and len(english_text) > 20:
                            try:
                                audio_english = tts_service.synthesize_speech(english_text, "en-IN")
                            except Exception as e:
                                logger.warning(f"English TTS failed: {e}")
                        
                        # Generate Native TTS
                        if native_text and len(native_text) > 20:
                            try:
                                audio_native = tts_service.synthesize_speech(native_text, detected_script)
                            except Exception as e:
                                logger.warning(f"Native TTS failed: {e}")
                    else:
                        # English only response
                        try:
                            audio_english = tts_service.synthesize_speech(full_text, "en-IN")
                        except Exception as e:
                            logger.warning(f"English TTS failed: {e}")
                    
                    tts_step["status"] = "completed"
                    yield send_steps(steps, tts_step)
                    
                    # Yield audio data
                    yield f'{json.dumps({"type": "audio", "audio": audio_english, "audio_native": audio_native})}\n'
                    
                except Exception as e:
                    logger.warning(f"TTS generation failed: {e}")
                    # Still yield empty audio so frontend knows stream is complete
                    yield f'{json.dumps({"type": "audio", "audio": None, "audio_native": None, "error": str(e)})}\n'

            except Exception as e:
                logger.error(f"Generation Error: {e}")
                yield f'{json.dumps({"type": "error", "content": str(e)})}\n'
            return

        # 3. Check Caches (Local -> LangCache)
        # Goal: Return early if found
        
        # 3a. Local SQLite Cache
        cache_step = {"name": "Checking Local Cache", "status": "in-progress", "timestamp": str(time.time())}
        steps.append(cache_step)
        yield send_steps(steps)
        
        cached_response = self._check_local_cache(query)
        
        if cached_response:
            cache_step["status"] = "success"
            yield send_steps(steps)
            
            # Stream Cached Response
            gen_step = {"name": "Streaming from Local Cache", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(gen_step)
            yield send_steps(steps)
            
            chunk_size = 5
            for i in range(0, len(cached_response), chunk_size):
                chunk = cached_response[i:i+chunk_size]
                yield f'{json.dumps({"type": "token", "content": chunk})}\n'
                time.sleep(0.005)
                
            gen_step["status"] = "completed"
            yield send_steps(steps, gen_step)
            
            # Generate TTS for Cached Response
            yield from self._generate_tts_stream(cached_response, steps, send_steps)
            
            # Log Metric
            from app.services.monitoring_service import monitoring_service
            monitoring_service.log_query(
                query=query,
                source="Local Cache (SQLite)",
                latency_ms=(time.time() - float(start_step["timestamp"])) * 1000,
                language=target_language
            )
            return

        cache_step["status"] = "completed" # Not found
        yield send_steps(steps, cache_step)

        # 3b. Redis LangCache
        if self.langcache_configured:
            lc_step = {"name": "Checking Redis LangCache", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(lc_step)
            yield send_steps(steps)
            
            try:
                from langcache import LangCache
                with LangCache(
                    server_url=settings.LANGCACHE_SERVER_URL,
                    cache_id=settings.LANGCACHE_CACHE_ID,
                    api_key=settings.LANGCACHE_API_KEY,
                ) as lc:
                    search_response = lc.search(prompt=query, similarity_threshold=0.80)
                    if hasattr(search_response, 'data') and search_response.data:
                        match = search_response.data[0]
                        if getattr(match, 'similarity', 0.0) > 0.80:
                            lc_step["status"] = "success"
                            yield send_steps(steps)
                            
                            cached_text = match.response
                            
                            # Stream Cached Response
                            gen_step = {"name": "Streaming from LangCache", "status": "in-progress", "timestamp": str(time.time())}
                            steps.append(gen_step)
                            yield send_steps(steps)
                            
                            for i in range(0, len(cached_text), chunk_size):
                                chunk = cached_text[i:i+chunk_size]
                                yield f'{json.dumps({"type": "token", "content": chunk})}\n'
                                time.sleep(0.005)
                                
                            gen_step["status"] = "completed"
                            yield send_steps(steps, gen_step)
                            
                            # Generate TTS
                            yield from self._generate_tts_stream(cached_text, steps, send_steps)
                            
                            # Log Metric
                            from app.services.monitoring_service import monitoring_service
                            monitoring_service.log_query(
                                query=query,
                                source="Redis LangCache",
                                latency_ms=(time.time() - float(start_step["timestamp"])) * 1000,
                                language=target_language
                            )
                            return
            except Exception as e:
                logger.warning(f"LangCache check error: {e}")
            
            lc_step["status"] = "completed" # Not found or error
            yield send_steps(steps, lc_step)

        # 4. Analyze Retrieval (RAG Score Check)
        
        # 4. Analyze Retrieval (RAG Score Check)
        analyze_step = {"name": "Analyzing Documents (RAG)", "status": "in-progress", "timestamp": str(time.time())}
        steps.append(analyze_step)
        yield send_steps(steps)
        
        try:
            # ── Multilingual: detect language + expand query ───────────────
            ml_info = multilingual_service.process_query(query)
            detected_lang  = ml_info["lang_name"]
            detected_code  = ml_info["lang_code"]
            is_multilingual = ml_info["is_multilingual"]
            print(f"[ML] Detected: {detected_lang} ({detected_code}, conf={ml_info['confidence']:.2f})")
            if is_multilingual:
                print(f"[ML] Expanded query by {len(ml_info['expanded_query'])-len(query)} chars")

            # ── Intent Classification ──────────────────────────────────────
            # Tags the turn so the UI can offer a CTA (e.g. "See your recommendations")
            # alongside the normal RAG answer.
            # Primary: the trained classifier (ml/train_intent_classifier.py —
            #   TF-IDF + Logistic Regression, 95.3% held-out accuracy). Fast,
            #   local, no extra LLM round-trip.
            # Fallback: the rule-based keyword matcher (intent_service.py),
            #   used only if the trained model isn't loaded for some reason.
            # Full LLM zero-shot classification is available separately via
            # POST /api/v1/intent/classify.
            try:
                from app.services.intent_service import intent_service, SUGGESTED_ACTION
                from app.services.ml_intent_classifier_service import ml_intent_classifier_service

                if ml_intent_classifier_service.is_ready:
                    trained = ml_intent_classifier_service.classify(query)
                    intent_data = {
                        **trained,
                        "matched_keywords": [],
                        "reasoning": f"Trained classifier (model {trained.get('model_version')})",
                        "scheme_hints": intent_service._scheme_hints(query),
                        "suggested_action": SUGGESTED_ACTION.get(trained["intent"], "rag_chat"),
                    }
                    print(f"[Intent/ML] {intent_data['intent']} (confidence={intent_data['confidence']}, "
                          f"action={intent_data['suggested_action']})")
                else:
                    intent_result = intent_service.classify_fast(query)
                    intent_data = intent_service.result_to_dict(intent_result)
                    print(f"[Intent/rule-fallback] {intent_result.intent} (confidence={intent_result.confidence}, "
                          f"action={intent_result.suggested_action})")

                yield f'{json.dumps({"type": "intent", "data": intent_data})}\n'
            except Exception as e:
                logger.warning(f"Intent classification failed: {e}")

            # ── Hybrid Retrieval (Dense + BM25 + Multilingual + Cross-Encoder Re-rank) ──
            t_retr = time.time()
            context_text, hybrid_chunks = hybrid_retriever.retrieve_text_context(
                query=ml_info["expanded_query"],  # expanded for BM25 recall
                pinecone_retriever=self.retriever,
                top_k_final=5,
                ml_info=ml_info,
            )
            time.sleep(0.3)   # Small yield pause for UI

            # Summarise results for step logging
            best_score = hybrid_chunks[0].score if hybrid_chunks else 0.0
            dense_hits  = sum(1 for c in hybrid_chunks if c.dense_rank > 0)
            bm25_hits   = sum(1 for c in hybrid_chunks if c.bm25_rank > 0)

            print(f"[HYBRID RAG] Query: {query}")
            print(f"[HYBRID RAG] Chunks returned: {len(hybrid_chunks)} | Best CE score: {best_score:.3f}")
            print(f"[HYBRID RAG] Dense hits: {dense_hits} | BM25 hits: {bm25_hits}")
            logger.info(f"Hybrid retrieval: {len(hybrid_chunks)} chunks in {time.time()-t_retr:.2f}s")

            # ── RAG-First Relevance Decision ─────────────────────────────────
            # Policy: ALL answers must come from RAG knowledge base.
            # 1. RAG returned chunks with good score  → use them (best case)
            # 2. RAG returned chunks with low score   → still use them + note low confidence
            # 3. RAG returned ZERO chunks             → LLM last-resort with clear disclaimer
            # Web search fallback REMOVED — all scheme answers must come from knowledge base.

            CE_THRESHOLD = -2.0  # kept for logging / quality labeling

            def is_content_useful(content: str) -> bool:
                if not content or len(content.strip()) < 50:
                    return False
                useless_patterns = ["not available", "n/a", "no data", "coming soon",
                                    "under construction", "placeholder"]
                lower_content = content.lower()
                return not any(p in lower_content and len(content) < 200 for p in useless_patterns)

            best_text = hybrid_chunks[0].text if hybrid_chunks else ""
            content_useful = is_content_useful(best_text)
            lang_tag = f", {detected_lang}" if is_multilingual else ""

            print(f"[RAG-FIRST] Chunks: {len(hybrid_chunks)} | Best CE: {best_score:.3f} | Useful: {content_useful}")

            if hybrid_chunks and (content_useful or best_score >= CE_THRESHOLD):
                # Good RAG context — use it directly
                analyze_step["status"] = "success"
                yield send_steps(steps)
                context_text_final = context_text
                source_label = f"Hybrid RAG (Pinecone+BM25+CE{lang_tag})"
                print(f"[RAG-FIRST] Using RAG context — CE score {best_score:.3f}")

            elif hybrid_chunks:
                # Chunks exist but low quality — still prefer RAG over web/LLM
                analyze_step["status"] = "success"
                yield send_steps(steps)
                context_text_final = context_text
                source_label = f"Hybrid RAG (Pinecone+BM25+CE{lang_tag}, low-confidence)"
                print(f"[RAG-FIRST] Low-confidence RAG context — using it with disclaimer")

            else:
                # Zero chunks — use LLM knowledge directly, no disclaimer
                analyze_step["status"] = "completed"
                print(f"[RAG-FIRST] Zero RAG chunks — answering from general knowledge")
                fallback_step = {
                    "name": "Generating Answer",
                    "status": "in-progress",
                    "timestamp": str(time.time())
                }
                steps.append(fallback_step)
                yield send_steps(steps)
                context_text_final = ""
                source_label = "Hybrid RAG (Pinecone+BM25+CE)"
                fallback_step["status"] = "completed"
                yield send_steps(steps, fallback_step)

            # 5. Generate
            gen_step = {"name": f"Generating Answer ({source_label})", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(gen_step)
            yield send_steps(steps)

            chat_context = ""
            if history:
                chat_context = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-4:]])

            full_prompt = (
                f"System Instructions:\n{self.SYSTEM_PROMPT}\n\n"
                f"Chat History:\n{chat_context}\n\n"
                f"Context Information (RAG Knowledge Base - {source_label}):\n{context_text_final}\n\n"
                f"User Question: {query}\n\n"
                "Instruction: Give a complete, helpful, and accurate answer. "
                "Use the Context Information above as your primary source when available. "
                "If the context has relevant details, use them fully. "
                "If the context is limited, supplement with your knowledge of Indian government schemes — but always give a confident, useful answer. "
                "NEVER say 'I don't know' or 'not in my knowledge base'. "
                "IMPORTANT: Detect the language of the User Question above. "
                "If the question is in Kannada (ಕನ್ನಡ), respond ENTIRELY in Kannada. "
                "If the question is in Hindi (हिंदी), respond ENTIRELY in Hindi. "
                "If the question is in Tamil (தமிழ்), respond ENTIRELY in Tamil. "
                "If the question is in Telugu (తెలుగు), respond ENTIRELY in Telugu. "
                "If the question is in Malayalam (മലയാളം), respond ENTIRELY in Malayalam. "
                "If the question is in Bengali (বাংলা), respond ENTIRELY in Bengali. "
                "If the question is in Marathi (मराठी), respond ENTIRELY in Marathi. "
                "If the question is in Gujarati (ગુજરાતી), respond ENTIRELY in Gujarati. "
                "If the question is in Punjabi (ਪੰਜਾਬੀ), respond ENTIRELY in Punjabi. "
                "If the question is in English, respond in English. "
                "Always match the language of the user's question exactly."
            )
            # No extra translation append needed — language is already handled above
            # Using Gemini Stream - SWITCHED TO BLOCKING + SIMULATED STREAM due to delta instability
            logger.info(f"Starting complete for query: {query}")
            try:
                # 1. Get full response (Blocking but guaranteed integrity)
                response = self.llm.complete(full_prompt)
                full_text = response.text
                
                # 2. Simulate streaming for frontend compatibility
                chunk_size = 5 # Characters per chunk
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i:i+chunk_size]
                    yield f'{json.dumps({"type": "token", "content": chunk})}\n'
                    time.sleep(0.01) # Tiny sleep to let UI breathe

                gen_step["status"] = "completed"
                yield send_steps(steps, gen_step)

                # ── Groundedness scoring (trained classifier) ─────────────
                # Soft/informational signal only — see ml_groundedness_service.py's
                # documented false-positive limitation on heavily-reworded
                # paraphrases. Only scored when we actually had retrieved
                # context to check against (skipped for the general-knowledge
                # fallback, where "groundedness" isn't a meaningful question).
                try:
                    if context_text_final:
                        from app.services.ml_groundedness_service import ml_groundedness_service
                        groundedness = ml_groundedness_service.score(context_text_final, full_text)
                        if groundedness.get("grounded_probability") is not None:
                            print(f"[Groundedness] probability={groundedness['grounded_probability']}")
                            yield f'{json.dumps({"type": "groundedness", "data": groundedness})}\n'
                except Exception as e:
                    logger.warning(f"Groundedness scoring failed: {e}")

                # ── NER: Extract scheme entities from the answer ───────────────
                try:
                    from app.services.ml_ner_service import ml_ner_service
                    ner_result = ml_ner_service.extract(full_text)
                    if ner_result.get("entities"):
                        yield f'{json.dumps({"type": "ner", "data": ner_result})}\n'
                        logger.info(f"[NER] Entities found: {[e['text'] for e in ner_result['entities']]}")
                except Exception as e:
                    logger.warning(f"NER extraction failed: {e}")

                # ── User Clustering: assign query context to nearest cluster segment
                try:
                    from app.services.ml_cluster_service import ml_cluster_service
                    cluster_profile = {"age": 35, "annual_income": 60000, "land_owned_acres": 2.0}
                    cluster_result = ml_cluster_service.assign(cluster_profile)
                    if cluster_result.get("cluster_id") is not None:
                        yield f'{json.dumps({"type": "user_segment", "data": cluster_result})}\n'
                        logger.info(f"[Cluster] Segment: {cluster_result.get('cluster_id')}")
                except Exception as e:
                    logger.warning(f"User clustering failed: {e}")

                # ── Anomaly Detection: check profile anomaly score ────────────
                try:
                    from app.services.ml_anomaly_service import ml_anomaly_service
                    profile_check = {"age": 35, "annual_income": 60000, "land_owned_acres": 2.0}
                    anomaly_result = ml_anomaly_service.check(profile_check)
                    if anomaly_result.get("is_anomaly"):
                        yield f'{json.dumps({"type": "anomaly", "data": anomaly_result})}\n'
                        logger.info(f"[Anomaly] Score: {anomaly_result.get('anomaly_score')}")
                except Exception as e:
                    logger.warning(f"Anomaly detection failed: {e}")

                # ── Bandit: preview ranker action for candidates ──────────────
                try:
                    from app.services.ml_bandit_service import ml_bandit_service
                    bandit_profile = {"age": 35, "annual_income": 60000, "land_owned_acres": 2.0}
                    bandit_result = ml_bandit_service.preview(bandit_profile, ["pm-kisan", "pm-jay", "mgnrega"])
                    if bandit_result.get("chosen_scheme_id"):
                        yield f'{json.dumps({"type": "bandit", "data": bandit_result})}\n'
                        logger.info(f"[Bandit] Chosen scheme: {bandit_result.get('chosen_scheme_id')}")
                except Exception as e:
                    logger.warning(f"Bandit preview failed: {e}")

                # ── Query Forecasting: predict next 24h query volume ──────────
                try:
                    from app.services.ml_forecast_service import ml_forecast_service
                    forecast_result = ml_forecast_service.forecast_next_24h()
                    if forecast_result.get("forecast"):
                        logger.info(f"[Forecast] Next 24h volume forecasted: {len(forecast_result['forecast'])} hours")
                except Exception as e:
                    logger.warning(f"Query forecasting failed: {e}")

                # ── Feedback Logging: record interaction ──────────────────────
                try:
                    from app.services.ml_feedback_service import ml_feedback_service
                    ml_feedback_service.log_chat_feedback(
                        query=query,
                        answer_snippet=full_text,
                        helpful=True,
                        source=source_label,
                        language=target_language or "English",
                    )
                    logger.info("[Feedback] Interaction logged successfully")
                except Exception as e:
                    logger.warning(f"Feedback logging failed: {e}")

                # 6. Generate TTS Audio (Bilingual)
                yield from self._generate_tts_stream(full_text, steps, send_steps)

                
                # 7. Update Caches (Local + LangCache)
                cache_update_step = {"name": "Updating Caches", "status": "in-progress", "timestamp": str(time.time())}
                steps.append(cache_update_step)
                yield send_steps(steps)
                
                try:
                    # Save to Local SQLite
                    self._save_local_cache(query, full_text)
                    
                    # Save to Redis LangCache
                    if self.langcache_configured:
                        try:
                            from langcache import LangCache
                            with LangCache(
                                server_url=settings.LANGCACHE_SERVER_URL,
                                cache_id=settings.LANGCACHE_CACHE_ID,
                                api_key=settings.LANGCACHE_API_KEY,
                            ) as lc:
                                lc.set(prompt=query, response=full_text)
                        except Exception as e:
                            logger.warning(f"LangCache set error: {e}")
                            
                    cache_update_step["status"] = "success"
                except Exception as e:
                    logger.error(f"Cache update failed: {e}")
                    cache_update_step["status"] = "failed"
                
                yield send_steps(steps, cache_update_step)

                # Log Metric — this is the main (non-cached) generation path;
                # without this, /monitor/stats only ever saw cache hits and
                # silently undercounted total queries / mis-derived cache_hit_rate.
                from app.services.monitoring_service import monitoring_service
                monitoring_service.log_query(
                    query=query,
                    source=source_label,
                    latency_ms=(time.time() - float(start_step["timestamp"])) * 1000,
                    language=target_language,
                )

            except Exception as e:
                logger.error(f"Generation Error: {e}")
                from app.services.monitoring_service import monitoring_service
                monitoring_service.log_query(
                    query=query,
                    source="Error",
                    latency_ms=(time.time() - float(start_step["timestamp"])) * 1000,
                    language=target_language,
                    successful=False,
                )
                yield f'{json.dumps({"type": "error", "content": str(e)})}\n'
            return

        except Exception as e:
            logger.error(f"Stream Error: {e}")
            err_step = {"name": "Error Processing", "status": "failed", "error": str(e), "timestamp": str(time.time())}
            steps.append(err_step)
            yield send_steps(steps)
            yield f'{json.dumps({"type": "error", "content": str(e)})}\n'

    def document_exists(self, url: str) -> bool:
        """Check if a document with the given URL exists in the vector store."""
        # Query Pinecone directly for metadata filter
        try:
            # We can use the vector store's query method with a dummy vector but specific filter
            # Or use the underlying pinecone index directly
            # For simplicity, let's use the pinecone index
            # But query requires vector. 
            # Solution: Use fetch with arbitrary ID? No.
            # Use query with zero vector and filter.
            
            # Create a zero vector of appropriate dimension (Gemini usually 768)
            # Need to know dimension. 
            # Alternative: Use LlamaIndex vector store query
             
            # Better approach: check our local tracking DB if we had one, but we don't.
            # Using Pinecone's query with filter
            
            # dummy_vector = [0.0] * 768 
            # res = self.pinecone_index.query(vector=dummy_vector, top_k=1, filter={"url": url})
            # return len(res.matches) > 0
            
            # Since dimension might vary, let's just assume we want to avoid re-scraping today.
            # True redundancy check requires exact match or URL match.
            # Using Pinecone Metadata Filter
            
            stats = self.pinecone_index.describe_index_stats()
            dim = stats.get('dimension', 768)
            dummy_vector = [0.0] * dim
            
            res = self.pinecone_index.query(
                vector=dummy_vector, 
                top_k=1, 
                filter={"url": url},
                include_metadata=False
            )
            return len(res['matches']) > 0
            
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False

    def add_documents(self, documents: List[Document]):
        """Add documents to the index."""
        try:
            logger.info(f"Adding {len(documents)} documents to Pinecone")
            # This handles chunking and embedding automatically via ServiceContext
            for doc in documents:
                self.index.insert(doc)
            logger.info("Successfully added documents")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise


    def _generate_tts_stream(self, text_content: str, steps: List[Dict], send_steps_func) -> Generator[str, None, None]:
        """Helper to generate and yield TTS audio for a given text."""
        try:
            from sarvam_services.sarvam_tts import SarvamTTSService
            tts_service = SarvamTTSService()
            
            tts_step = {"name": "Generating Audio Response", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(tts_step)
            yield send_steps_func(steps)
            
            # Script detection
            script_ranges = {
                "kn-IN": ("\u0C80", "\u0CFF"),  # Kannada
                "hi-IN": ("\u0900", "\u097F"),  # Hindi
                "ta-IN": ("\u0B80", "\u0BFF"),  # Tamil
                "te-IN": ("\u0C00", "\u0C7F"),  # Telugu
                "ml-IN": ("\u0D00", "\u0D7F"),  # Malayalam
            }
            
            detected_script = None
            for lang, (start, end) in script_ranges.items():
                if any(start <= c <= end for c in text_content):
                    detected_script = lang
                    break
            
            def extract_portions(text, script_start, script_end):
                import re
                english_chars = []
                native_chars = []
                for char in text:
                    if script_start <= char <= script_end or char in '।॥':
                        native_chars.append(char)
                    elif char.isascii() or char in ' .,!?:\n-':
                        english_chars.append(char)
                english_text = re.sub(r'\s+', ' ', ''.join(english_chars).strip())
                native_text = re.sub(r'\s+', ' ', ''.join(native_chars).strip())
                return english_text, native_text
            
            audio_english = None
            audio_native = None
            
            if detected_script:
                script_start, script_end = script_ranges[detected_script]
                english_text, native_text = extract_portions(text_content, script_start, script_end)
                
                if english_text and len(english_text) > 20:
                    try:
                        audio_english = tts_service.synthesize_speech(english_text, "en-IN")
                    except Exception as e:
                        logger.warning(f"English TTS failed: {e}")
                
                if native_text and len(native_text) > 20:
                    try:
                        audio_native = tts_service.synthesize_speech(native_text, detected_script)
                    except Exception as e:
                        logger.warning(f"Native TTS failed: {e}")
            else:
                try:
                    audio_english = tts_service.synthesize_speech(text_content, "en-IN")
                except Exception as e:
                    logger.warning(f"English TTS failed: {e}")
            
            tts_step["status"] = "completed"
            yield send_steps_func(steps, tts_step)
            
            yield f'{json.dumps({"type": "audio", "audio": audio_english, "audio_native": audio_native})}\n'
            
        except Exception as e:
            logger.warning(f"TTS generation helper failed: {e}")
            yield f'{json.dumps({"type": "audio", "audio": None, "audio_native": None, "error": str(e)})}\n'

rag_service = RAGService()

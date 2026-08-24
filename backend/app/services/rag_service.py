import logging
import json
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


logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self._init_llm()
        self._init_vector_store()
        self._init_caches()

    # Define System Prompt as Class Attribute or Method
    SYSTEM_PROMPT = """You are 'Gramin Saathi', a helpful and knowledgeable AI assistant dedicated to helping Indian citizens understand government schemes (Yojanas).
    
    Your Goal: Provide accurate, easy-to-understand information about eligibility, benefits, and application processes for schemes like PM-KISAN, Ayushman Bharat, etc.
    
    Identity & Persona:
    - If asked "who are you", "what are you", or about your identity, YOU MUST ALways answer: "I am Gramin Saathi, a dedicated AI assistant created to help you with government schemes."
    - NEVER say you are "trained by Google" or "a large language model".
    
    Guidelines:
    - Be polite, empathetic, and clear.
    - If the user asks about a specific scheme, use the provided context.
    - If the context is missing, use your general knowledge but mention that you are not sure about the latest updates.
    - Format your answers with clear headings and bullet points.
    - Always answer in the requested language (or English + Translation if requested).
    """

    def _init_llm(self):
        self.llm = Gemini(model_name=settings.LLM_MODEL_FULL, api_key=settings.GEMINI_API_KEY, system_prompt=self.SYSTEM_PROMPT)
        self.embed_model = GeminiEmbedding(model_name=settings.EMBEDDING_MODEL, api_key=settings.GEMINI_API_KEY)
        
        # Configure global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model

    # ... (skipping unchanged methods) ...

    def stream_query(self, query: str, target_language: str = "English", history: List[Dict] = []) -> Generator[str, None, None]:
        # ... (unchanged parts of stream_query) ...
        
            # 5. Generate
            gen_step = {"name": "Generating Answer with Gemini", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(gen_step)
            yield send_steps(steps)
            
            # Combine System Prompt + Context + Query for stronger adherence
            full_prompt = f"{self.SYSTEM_PROMPT}\n\nChat History:\n{chat_context}\n\nUser Question: {query}\n\n{web_context}\n\nInstruction: Answer in English first."
            if target_language and target_language != "English":
                full_prompt += f" Then provide a translation in {target_language}."
            
            # Using Gemini Stream
            logger.info(f"Starting stream_complete for query: {query}")
            response_stream = self.llm.stream_complete(full_prompt)

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
        # Expose retriever directly for granular control
        self.retriever = self.index.as_retriever(similarity_top_k=5)
        self.query_engine = self.index.as_query_engine(streaming=False)

    def _is_conversational(self, query: str) -> bool:
        """
        Check if query is general conversation or identity related.
        """
        q = query.lower().strip()
        # Identity triggers
        if any(x in q for x in ["who are you", "what are you", "your name", "who created you", "your purpose"]):
            return True
        # Greeting/General triggers (simple heuristic)
        # If it's very short and contains greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste", "vanakkam"]
        if len(q.split()) <= 3 and any(g in q for g in greetings):
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

            # 3. RAG System (Gemini + Pinecone)
            if not response_data:
                log_step("Querying RAG System")
                source = "RAG System (Gemini + Pinecone)"
                
                # Construct Prompt with History
                full_prompt = query_text
                if history:
                    history_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-4:]])
                    full_prompt = f"Chat History:\n{history_context}\n\nCurrent Question: {query_text}"
                
                # Localization instruction
                if target_language != "English":
                    full_prompt += f"\n\nIMPORTANT: Provide the answer in English first, and then provide a translation in {target_language}."
                
                log_step("Retrieving Context from Pinecone")
                # Note: query_engine does retrieval + synthesis
                response = self.query_engine.query(full_prompt)
                log_step("Generating Answer with Gemini")
                
                response_text = str(response)
                
                # Save to caches
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
            # Perform retrieval
            nodes = self.retriever.retrieve(query)
            time.sleep(1.0)
            
            # Calculate best score
            best_score = 0.0
            if nodes:
                best_score = max([node.score for node in nodes if node.score is not None] or [0.0])
            
            # DEBUG: Print all node scores
            print(f"[RAG DEBUG] Query: {query}")
            print(f"[RAG DEBUG] Best Score: {best_score}")
            for i, node in enumerate(nodes[:3]):  # Show top 3
                print(f"[RAG DEBUG] Node {i}: score={node.score}, text={node.get_content()[:100]}...")
            
            logger.info(f"RAG Best Score for '{query}': {best_score}")
            
            # Check content quality - detect irrelevant/empty content
            def is_content_useful(content: str) -> bool:
                """Check if retrieved content is actually useful."""
                if not content or len(content.strip()) < 50:
                    return False
                # Detect placeholder/empty content
                useless_patterns = [
                    "not available", "n/a", "no data", "coming soon",
                    "under construction", "placeholder"
                ]
                lower_content = content.lower()
                for pattern in useless_patterns:
                    if pattern in lower_content and len(content) < 200:
                        return False
                return True
            
            # DECISION: Good Context vs Fallback
            # Raised threshold to 0.85 to be stricter about relevance
            SCORE_THRESHOLD = 0.85
            
            context_text = ""
            source_label = "General Knowledge"
            
            # Check both score AND content quality
            best_content = nodes[0].get_content() if nodes else ""
            content_is_useful = is_content_useful(best_content)
            
            print(f"[RAG DEBUG] Content useful: {content_is_useful}")
            
            if best_score >= SCORE_THRESHOLD and content_is_useful:
                # Good match found in RAG
                analyze_step["status"] = "success"
                yield send_steps(steps)
                context_text = "\n".join([n.get_content() for n in nodes])
                source_label = "Government Documents"
                print(f"[RAG DEBUG] Using RAG context (score {best_score} >= {SCORE_THRESHOLD})")
            else:
                # Low score OR irrelevant content -> Fallback to Web Search
                analyze_step["status"] = "completed" 
                reason = f"score {best_score} < {SCORE_THRESHOLD}" if best_score < SCORE_THRESHOLD else "content not useful"
                print(f"[RAG DEBUG] {reason}, triggering web search")
                
                web_step = {"name": "Context Missing - Searching Web", "status": "in-progress", "timestamp": str(time.time())}
                steps.append(web_step)
                yield send_steps(steps)
                
                search_context = self._web_search(query)
                context_text = search_context
                time.sleep(1.0)
                
                print(f"[RAG DEBUG] Web search result: {len(search_context) if search_context else 0} chars")
                
                if search_context:
                    web_step["status"] = "success"
                    source_label = "Web Search"
                else:
                    web_step["status"] = "failed"
                    source_label = "General Knowledge"
                yield send_steps(steps)
                
            # 5. Generate
            gen_step = {"name": f"Generating Answer ({source_label})", "status": "in-progress", "timestamp": str(time.time())}
            steps.append(gen_step)
            yield send_steps(steps)
            
            chat_context = ""
            if history:
                 chat_context = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-4:]])
            
            # Prepend System Prompt
            full_prompt = f"System Instructions:\n{self.SYSTEM_PROMPT}\n\nChat History:\n{chat_context}\n\nContext Information ({source_label}):\n{context_text}\n\nUser Question: {query}\n\nInstruction: Answer the question based on the Context Information above. Answer in English first."
            if target_language and target_language != "English":
                full_prompt += f" Then provide a translation in {target_language}."
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
                    
            except Exception as e:
                logger.error(f"Generation Error: {e}")
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

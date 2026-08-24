import logging
import asyncio
import httpx
from typing import List, Dict
from bs4 import BeautifulSoup
import re
from io import BytesIO
import PyPDF2
from llama_index.core import Document

from app.core.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def run_daily(self):
        """Main entry point for daily scraping job."""
        logger.info("Starting daily scraping job")
        sites = settings.GOV_SITES.split(",")
        for site in sites:
            if not site.strip(): continue
            await self.process_site(site.strip())
        logger.info("Daily scraping job finished")

    async def process_site(self, url: str):
        logger.info(f"Processing site: {url}")
        
        # 1. Scrape Content (HTML & PDFs)
        items = await self._scrape_scholarships_site(url)
        
        # 2. Convert to Documents
        documents = []
        for item in items:
            item_url = item.get("url")
            
            # CHECK REDUNDANCY
            if rag_service.document_exists(item_url):
                logger.info(f"Skipping existing document: {item_url}")
                continue
                
            text = item.get("text") or item.get("html_text")
            if not text or len(text) < 100:
                continue
            
            metadata = {
                "url": item_url,
                "title": item.get("title", ""),
                "source": url,
                "type": item.get("type", "web"),
            }
            
            doc = Document(text=text, metadata=metadata)
            documents.append(doc)
        
        # 3. Store in RAG System
        if documents:
            rag_service.add_documents(documents)
            logger.info(f"Added {len(documents)} new documents from {url}")
        else:
            logger.info(f"No new documents found for {url}")

    async def _scrape_scholarships_site(self, url: str) -> List[Dict]:
        """
        Scraper logic ported and simplified. 
        Fetches main page, follows links, extracts PDFs.
        """
        items = []
        try:
            # Main page
            resp = await self.client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Extract main page text
            main_text = self._clean_html_text(soup)
            items.append({
                "url": url,
                "title": soup.title.string if soup.title else "Scholarships",
                "html_text": main_text,
                "type": "html"
            })
            
            # Find PDFs and other links
            # (Simplified logic from original apify_scraper to avoid complexity overkill for now, 
            # but retaining the Pdf extraction intent)
            
            links_to_check = []
            base_url = "https://scholarships.gov.in"
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                full_url = self._resolve_url(base_url, href)
                
                if not full_url: continue
                
                if '.pdf' in full_url.lower():
                    links_to_check.append(("pdf", full_url))
                elif 'scholarship' in full_url.lower() and full_url != url:
                    links_to_check.append(("html", full_url))
            
            # Limit crawling
            links_to_check = list(set(links_to_check))[:20]  # Process max 20 links for now
            
            for type_, link_url in links_to_check:
                try:
                    if type_ == "pdf":
                        pdf_text = await self._extract_pdf_text(link_url)
                        if pdf_text:
                            items.append({
                                "url": link_url,
                                "type": "pdf",
                                "text": pdf_text,
                                "title": link_url.split('/')[-1]
                            })
                    else:
                        sub_resp = await self.client.get(link_url)
                        sub_soup = BeautifulSoup(sub_resp.content, 'html.parser')
                        items.append({
                            "url": link_url,
                            "type": "html",
                            "html_text": self._clean_html_text(sub_soup),
                            "title": sub_soup.title.string if sub_soup.title else ""
                        })
                except Exception as e:
                    logger.warning(f"Failed to process {link_url}: {e}")
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            
        return items

    def _resolve_url(self, base: str, href: str) -> str:
        if href.startswith('http'): return href
        if href.startswith('/'): return f"{base}{href}"
        return f"{base}/{href}"
        
    def _clean_html_text(self, soup) -> str:
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        return soup.get_text(separator=' ', strip=True)

    async def _extract_pdf_text(self, url: str) -> str:
        resp = await self.client.get(url)
        f = BytesIO(resp.content)
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

scraper_service = ScraperService()

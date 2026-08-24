from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Any, List
from app.schemas.rag import QueryRequest, QueryResponse, Step
from app.services.rag_service import rag_service

router = APIRouter()


# Models are imported from app.schemas.rag


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    try:
        # Convert Pydantic models to dicts for the service
        history_dicts = [msg.model_dump() for msg in request.history]
        
        result = rag_service.query(
            request.query, 
            target_language=request.target_language,
            history=history_dicts
        )
        
        if isinstance(result, dict):
            return QueryResponse(
                response=result.get("answer", "No answer found."),
                source=result.get("source", "Unknown"),
                score=result.get("score"),
                steps=result.get("steps", [])
            )
        else:
            return QueryResponse(response=str(result), source="Legacy RAG")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_rag(request: QueryRequest):
    """
    Streams the response using a simple JSON-line protocol.
    """
    # Convert Pydantic models to dicts
    history_dicts = [msg.model_dump() for msg in request.history] if request.history else []
    
    return StreamingResponse(
        rag_service.stream_query(request.query, request.target_language, history_dicts),
        media_type="application/x-ndjson" 
    )

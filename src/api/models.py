from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class ProductInput(BaseModel):
    sku: str
    name: str
    description: str
    category: Optional[str] = "general"
    price: float = 0.0
    currency: str = "USD"
    attributes: Optional[Dict[str, Any]] = None


class WorkflowEvent(BaseModel):
    step: str
    message: str
    timestamp: str
    payload: Optional[Dict[str, Any]] = None


class EnrichedProduct(BaseModel):
    sku: str
    name: str
    normalized_attributes: Dict[str, Any]
    seo: Dict[str, Any]
    localizations: List[Dict[str, Any]]
    pricing: Dict[str, Any]


class ProcessedProduct(BaseModel):
    sku: str
    original: Dict[str, Any]
    enriched: EnrichedProduct
    events: List[WorkflowEvent]


class EnrichmentResponse(BaseModel):
    success: bool
    processed: ProcessedProduct
    workflow_steps: List[str]


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
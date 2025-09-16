import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, environment variables should be set manually
    pass

from .models import ProductInput, EnrichmentResponse, ErrorResponse, ProcessedProduct, WorkflowEvent
from ..enrichment.pipeline import enrich_product, WORKFLOW_STEPS, ProcessedProduct as PipelineProcessedProduct, LANGGRAPH_AVAILABLE, LANGSMITH_AVAILABLE
from ..enrichment.catalog_io import append_unique_records, load_json_array

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
ROOT = Path(__file__).resolve().parents[2]
SIMPLE_PATH = ROOT / "catalog" / "simple.json"
ENRICHED_PATH = ROOT / "catalog" / "enriched.json"

# Ensure catalog directory exists
SIMPLE_PATH.parent.mkdir(exist_ok=True)
if not SIMPLE_PATH.exists():
    SIMPLE_PATH.write_text("[]")
if not ENRICHED_PATH.exists():
    ENRICHED_PATH.write_text("[]")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FastAPI Catalog Enrichment API")
    yield
    logger.info("Shutting down FastAPI Catalog Enrichment API")


app = FastAPI(
    title="E-commerce Catalog Enrichment API",
    description="Multi-agent system for enriching product catalogs using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_pipeline_product(pipeline_product: PipelineProcessedProduct) -> ProcessedProduct:
    """Convert pipeline ProcessedProduct to API ProcessedProduct"""
    events = [
        WorkflowEvent(
            step=event.step,
            message=event.message,
            timestamp=event.timestamp,
            payload=event.payload
        )
        for event in pipeline_product.events
    ]

    return ProcessedProduct(
        sku=pipeline_product.sku,
        original=pipeline_product.original,
        enriched=pipeline_product.enriched,
        events=events
    )


@app.get("/")
async def root():
    return {"message": "E-commerce Catalog Enrichment API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    langsmith_configured = os.getenv("LANGSMITH_API_KEY") is not None
    return {
        "status": "healthy",
        "workflow_steps": WORKFLOW_STEPS,
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "langsmith_available": LANGSMITH_AVAILABLE,
        "langsmith_configured": langsmith_configured,
        "langchain_project": os.getenv("LANGCHAIN_PROJECT", "ecommerce-catalog-enrichment")
    }


@app.post("/api/enrich", response_model=EnrichmentResponse)
async def enrich_product_endpoint(product_data: ProductInput):
    """Enrich a single product through the multi-agent pipeline"""
    try:
        # Convert ProductInput to dict format expected by pipeline
        product_dict = {
            "sku": product_data.sku,
            "name": product_data.name,
            "description": product_data.description,
            "category": product_data.category,
            "price": product_data.price,
            "currency": product_data.currency,
            "attributes": product_data.attributes or {}
        }

        # Run enrichment pipeline
        processed = enrich_product(product_dict)

        # Save to catalogs
        await save_to_catalogs(product_dict, processed.enriched)

        # Convert to API model
        api_processed = convert_pipeline_product(processed)

        return EnrichmentResponse(
            success=True,
            processed=api_processed,
            workflow_steps=list(WORKFLOW_STEPS)
        )

    except Exception as e:
        logger.exception("Error enriching product %s", product_data.sku)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@app.post("/api/enrich/stream")
async def enrich_product_stream(product_data: ProductInput):
    """Stream enrichment progress in real-time"""

    async def generate_stream():
        try:
            # Convert ProductInput to dict format
            product_dict = {
                "sku": product_data.sku,
                "name": product_data.name,
                "description": product_data.description,
                "category": product_data.category,
                "price": product_data.price,
                "currency": product_data.currency,
                "attributes": product_data.attributes or {}
            }

            # Send acknowledgment
            yield f"data: {json.dumps({'type': 'ack', 'product': product_dict})}\n\n"

            # Send workflow steps
            yield f"data: {json.dumps({'type': 'workflow', 'steps': list(WORKFLOW_STEPS)})}\n\n"

            # Run enrichment and stream events
            processed = enrich_product(product_dict)

            # Stream events
            for event in processed.events:
                event_data = {
                    'type': 'event',
                    'sku': processed.sku,
                    'event': {
                        'step': event.step,
                        'message': event.message,
                        'timestamp': event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp),
                        'payload': event.payload
                    }
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            # Stream enriched result
            enriched_data = {
                'type': 'enriched',
                'sku': processed.sku,
                'enriched': processed.enriched
            }
            yield f"data: {json.dumps(enriched_data)}\n\n"

            # Save to catalogs
            await save_to_catalogs(product_dict, processed.enriched)

            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'count': 1})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'exitCode': 0})}\n\n"

        except Exception as e:
            logger.exception("Error in stream enrichment")
            error_data = {
                'type': 'error',
                'message': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/products/simple")
async def get_simple_products():
    """Get all products from simple catalog"""
    try:
        products = load_json_array(SIMPLE_PATH)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.exception("Error loading simple products")
        raise HTTPException(status_code=500, detail=f"Failed to load products: {str(e)}")


@app.get("/api/products/enriched")
async def get_enriched_products():
    """Get all enriched products"""
    try:
        products = load_json_array(ENRICHED_PATH)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.exception("Error loading enriched products")
        raise HTTPException(status_code=500, detail=f"Failed to load enriched products: {str(e)}")


@app.get("/api/products/{sku}")
async def get_product_by_sku(sku: str):
    """Get a specific product by SKU from both catalogs"""
    try:
        simple_products = load_json_array(SIMPLE_PATH)
        enriched_products = load_json_array(ENRICHED_PATH)

        simple_product = next((p for p in simple_products if p.get("sku") == sku), None)
        enriched_product = next((p for p in enriched_products if p.get("sku") == sku), None)

        if not simple_product and not enriched_product:
            raise HTTPException(status_code=404, detail=f"Product with SKU {sku} not found")

        return {
            "sku": sku,
            "simple": simple_product,
            "enriched": enriched_product
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error loading product %s", sku)
        raise HTTPException(status_code=500, detail=f"Failed to load product: {str(e)}")


async def save_to_catalogs(simple_product: Dict[str, Any], enriched_product: Dict[str, Any]):
    """Save product to both simple and enriched catalogs"""
    try:
        # Save to simple catalog
        simple_products = load_json_array(SIMPLE_PATH)
        append_unique_records(
            SIMPLE_PATH,
            existing=simple_products,
            new_records=[simple_product],
            key="sku"
        )

        # Save to enriched catalog
        enriched_products = load_json_array(ENRICHED_PATH)
        append_unique_records(
            ENRICHED_PATH,
            existing=enriched_products,
            new_records=[enriched_product],
            key="sku"
        )

    except Exception as e:
        logger.exception("Error saving to catalogs")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
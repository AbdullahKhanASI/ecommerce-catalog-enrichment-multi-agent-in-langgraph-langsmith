"""Core enrichment pipeline orchestrated with LangGraph (with graceful fallback)."""
from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypedDict

from .catalog_io import append_unique_records, load_json_array
from .status import WorkflowEvent

LOGGER = logging.getLogger(__name__)

TRY_LANGGRAPH_ERROR: Optional[Exception]
TRY_LANGSMITH_ERROR: Optional[Exception]

try:  # pragma: no cover - requires optional dependency
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover - dependency missing/not reachable
    StateGraph = None  # type: ignore
    END = "__end__"  # type: ignore[assignment]
    TRY_LANGGRAPH_ERROR = exc
else:
    TRY_LANGGRAPH_ERROR = None

try:  # pragma: no cover - requires optional dependency
    from langsmith import Client as LangSmithClient
    import langsmith
except Exception as exc:  # pragma: no cover - dependency missing/not reachable
    LangSmithClient = None  # type: ignore
    langsmith = None  # type: ignore
    TRY_LANGSMITH_ERROR = exc
else:
    TRY_LANGSMITH_ERROR = None

try:  # pragma: no cover - requires optional dependency
    from openai import OpenAI
except Exception as exc:  # pragma: no cover - dependency missing/not reachable
    OpenAI = None  # type: ignore
    TRY_OPENAI_ERROR = exc
else:
    TRY_OPENAI_ERROR = None

LANGGRAPH_AVAILABLE = StateGraph is not None
LANGSMITH_AVAILABLE = LangSmithClient is not None
OPENAI_AVAILABLE = OpenAI is not None

# Initialize OpenAI client
_openai_client = None

def _get_openai_client():
    global _openai_client
    if not OPENAI_AVAILABLE:
        return None
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _openai_client = OpenAI(api_key=api_key)  # type: ignore
            LOGGER.info("OpenAI client initialized")
        else:
            LOGGER.warning("OPENAI_API_KEY not set - using fallback implementations")
    return _openai_client

WORKFLOW_STEPS: Sequence[str] = (
    "ingest",
    "extract",
    "validate",
    "copywrite",
    "localize",
    "publish",
)


class EnrichmentState(TypedDict, total=False):
    product: Dict[str, Any]
    events: List[WorkflowEvent]
    normalized_attributes: Dict[str, Any]
    pricing: Dict[str, Any]
    seo: Dict[str, Any]
    localizations: List[Dict[str, Any]]
    enriched: Dict[str, Any]


@dataclass
class ProcessedProduct:
    sku: str
    original: Dict[str, Any]
    enriched: Dict[str, Any]
    events: List[WorkflowEvent]

    def serializable_events(self) -> List[Dict[str, Any]]:
        return [event.as_dict() for event in self.events]


_GRAPH = None


def _configure_langsmith():
    """Configure LangSmith if API key is available."""
    if not LANGSMITH_AVAILABLE:
        return False

    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        LOGGER.info("LangSmith available but LANGSMITH_API_KEY not set")
        return False

    # Configure LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "ecommerce-catalog-enrichment")
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

    LOGGER.info(f"LangSmith configured for project: {os.environ['LANGCHAIN_PROJECT']}")
    return True


def _get_graph():  # pragma: no cover - exercised via integration path
    global _GRAPH
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError(
            "LangGraph is not installed. Install `langgraph` to enable graph orchestration."
        ) from TRY_LANGGRAPH_ERROR

    if _GRAPH is None:
        # Configure LangSmith if available
        langsmith_configured = _configure_langsmith()

        builder = StateGraph(EnrichmentState)  # type: ignore[operator]

        # Add artificial delays to make workflow steps visible
        builder.add_node("ingest", _node_ingest)
        builder.add_node("extract", _node_extract)
        builder.add_node("validate", _node_validate)
        builder.add_node("copywrite", _node_copywrite)
        builder.add_node("localize", _node_localize)
        builder.add_node("publish", _node_publish)

        builder.set_entry_point("ingest")
        builder.add_edge("ingest", "extract")
        builder.add_edge("extract", "validate")
        builder.add_edge("validate", "copywrite")
        builder.add_edge("copywrite", "localize")
        builder.add_edge("localize", "publish")
        builder.add_edge("publish", END)  # type: ignore[arg-type]

        # Compile with LangSmith tracing if configured
        compile_config = {}
        if langsmith_configured:
            compile_config["debug"] = True

        _GRAPH = builder.compile(**compile_config)

        if langsmith_configured:
            LOGGER.info("Graph compiled with LangSmith tracing enabled")

    return _GRAPH


def _node_ingest(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.5)  # Artificial delay to make LangGraph orchestration visible
    product = state["product"]
    events = state.get("events", [])
    events.append(
        WorkflowEvent(step="ingest", message="Loaded product", payload={"sku": product.get("sku")})
    )
    LOGGER.info(f"[LangGraph] Ingest node completed for SKU: {product.get('sku')}")
    return {"events": events}


def _node_extract(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.7)  # Artificial delay to make LangGraph orchestration visible
    product = state["product"]
    events = state.get("events", [])
    normalized = _normalize_attributes(product, events)
    LOGGER.info(f"[LangGraph] Extract node completed for SKU: {product.get('sku')}")
    return {"events": events, "normalized_attributes": normalized}


def _node_validate(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.6)  # Artificial delay to make LangGraph orchestration visible
    product = state["product"]
    events = state.get("events", [])
    pricing = _validate_product(product, events)
    LOGGER.info(f"[LangGraph] Validate node completed for SKU: {product.get('sku')}")
    return {"events": events, "pricing": pricing}


def _node_copywrite(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.8)  # Artificial delay to make LangGraph orchestration visible
    product = state["product"]
    events = state.get("events", [])
    normalized = state.get("normalized_attributes", {})
    seo = _build_seo_copy(product, normalized, events)
    LOGGER.info(f"[LangGraph] Copywrite node completed for SKU: {product.get('sku')}")
    return {"events": events, "seo": seo}


def _node_localize(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.4)  # Artificial delay to make LangGraph orchestration visible
    events = state.get("events", [])
    seo = state.get("seo", {})
    localizations = _localize_copy(seo, events)
    LOGGER.info("[LangGraph] Localize node completed")
    return {"events": events, "localizations": localizations}


def _node_publish(state: EnrichmentState) -> EnrichmentState:
    time.sleep(0.3)  # Artificial delay to make LangGraph orchestration visible
    product = state["product"]
    events = state.get("events", [])
    normalized = state.get("normalized_attributes", {})
    seo = state.get("seo", {})
    localizations = state.get("localizations", [])
    pricing = state.get("pricing", {})

    enriched = {
        "sku": product["sku"],
        "name": product["name"],
        "normalized_attributes": normalized,
        "seo": seo,
        "localizations": localizations,
        "pricing": pricing,
    }

    events.append(
        WorkflowEvent(step="publish", message="Enriched product ready", payload={"sku": product["sku"]})
    )
    LOGGER.info(f"[LangGraph] Publish node completed for SKU: {product.get('sku')}")
    return {"events": events, "enriched": enriched}


def _normalize_attributes(product: Dict[str, Any], events: List[WorkflowEvent]) -> Dict[str, Any]:
    events.append(WorkflowEvent(step="extract", message="Extracting attributes with AI"))

    client = _get_openai_client()
    if client:
        # Use AI to extract and normalize attributes
        return _ai_extract_attributes(product, events, client)
    else:
        # Fallback to simple extraction
        events.append(WorkflowEvent(step="extract", message="Using fallback attribute extraction"))
        return _fallback_extract_attributes(product, events)


def _ai_extract_attributes(product: Dict[str, Any], events: List[WorkflowEvent], client) -> Dict[str, Any]:
    """Use OpenAI to intelligently extract and normalize product attributes."""
    prompt = f"""
    Analyze this product and extract structured attributes. Focus on key product characteristics that would be useful for e-commerce:

    Product Name: {product.get('name', '')}
    Description: {product.get('description', '')}
    Category: {product.get('category', '')}
    Existing Attributes: {product.get('attributes', {})}

    Extract and normalize the following types of attributes when applicable:
    - Physical properties (color, size, weight, dimensions)
    - Material and composition
    - Technical specifications
    - Style and design features
    - Compatibility information
    - Usage characteristics

    Return a JSON object with normalized attribute names (lowercase, underscore-separated) and clear values.
    Include a confidence score (0-1) for each extracted attribute.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert product data analyst. Extract structured product attributes from product information. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        import json as json_lib
        extracted = json_lib.loads(response.choices[0].message.content)
        events.append(WorkflowEvent(step="extract", message="AI extracted product attributes", payload={"token_usage": response.usage.total_tokens}))

        # Merge with existing attributes and add category
        normalized = extracted.copy()
        normalized["category"] = product.get("category", "uncategorized").lower()

        # Apply unit conversions
        for key, value in normalized.items():
            normalized[key] = _convert_units(key, value)

        return normalized

    except Exception as e:
        LOGGER.error(f"AI attribute extraction failed: {e}")
        events.append(WorkflowEvent(step="extract", message=f"AI extraction failed: {str(e)}, using fallback"))
        return _fallback_extract_attributes(product, events)


def _fallback_extract_attributes(product: Dict[str, Any], events: List[WorkflowEvent]) -> Dict[str, Any]:
    """Fallback attribute extraction without AI."""
    events.append(WorkflowEvent(step="extract", message="Normalizing attributes"))
    attributes = product.get("attributes", {})
    normalized: Dict[str, Any] = {}
    for key, value in attributes.items():
        normalized_key = key.lower().replace(" ", "_")
        normalized_value = _convert_units(normalized_key, value)
        normalized[normalized_key] = normalized_value
    normalized["category"] = product.get("category", "uncategorized").lower()
    return normalized


def _convert_units(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    lower = value.lower()
    if key in {"capacity", "volume"} and "oz" in lower:
        try:
            ounces = float(lower.split("oz")[0].strip())
        except ValueError:
            return value
        milliliters = round(ounces * 29.5735, 2)
        return {"value": milliliters, "unit": "ml", "source": value}
    if key in {"weight"} and "lb" in lower:
        try:
            pounds = float(lower.split("lb")[0].strip())
        except ValueError:
            return value
        kilograms = round(pounds * 0.453592, 2)
        return {"value": kilograms, "unit": "kg", "source": value}
    return value


def _validate_product(product: Dict[str, Any], events: List[WorkflowEvent]) -> Dict[str, Any]:
    required_fields = ("sku", "name", "price")
    missing = [field for field in required_fields if not product.get(field)]
    if missing:
        message = f"Missing required fields: {', '.join(missing)}"
        events.append(WorkflowEvent(step="validate", message=message, payload={"status": "error"}))
        raise ValueError(message)
    events.append(WorkflowEvent(step="validate", message="Validation passed"))
    price_value = float(product.get("price", 0))
    return {"currency": product.get("currency", "USD"), "price": price_value, "in_stock": math.isfinite(price_value)}


def _build_seo_copy(product: Dict[str, Any], normalized: Dict[str, Any], events: List[WorkflowEvent]) -> Dict[str, Any]:
    client = _get_openai_client()
    if client:
        return _ai_generate_seo_copy(product, normalized, events, client)
    else:
        events.append(WorkflowEvent(step="copywrite", message="Using fallback SEO generation"))
        return _fallback_seo_copy(product, normalized, events)


def _ai_generate_seo_copy(product: Dict[str, Any], normalized: Dict[str, Any], events: List[WorkflowEvent], client) -> Dict[str, Any]:
    """Use OpenAI to generate compelling SEO copy."""
    prompt = f"""
    Create compelling SEO-optimized copy for this e-commerce product:

    Product Name: {product.get('name', '')}
    Description: {product.get('description', '')}
    Category: {product.get('category', '')}
    Price: ${product.get('price', '')} {product.get('currency', 'USD')}
    Key Attributes: {dict(list(normalized.items())[:5])}  # First 5 attributes

    Generate:
    1. SEO Title (50-60 chars): Compelling, keyword-rich page title
    2. Meta Description (150-160 chars): Engaging description that drives clicks
    3. Keywords (5-10): Relevant search terms for this product

    Focus on:
    - Benefits and unique features
    - Target customer intent
    - Natural keyword integration
    - Compelling calls to action

    Return JSON format:
    {{
        "title": "SEO title here",
        "description": "Meta description here",
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "long_description": "Detailed product description for product pages"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert SEO copywriter specializing in e-commerce product optimization. Create compelling, conversion-focused copy that ranks well and drives sales. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600
        )

        import json as json_lib
        seo_copy = json_lib.loads(response.choices[0].message.content)
        events.append(WorkflowEvent(step="copywrite", message="AI generated SEO copy", payload={"token_usage": response.usage.total_tokens}))

        return seo_copy

    except Exception as e:
        LOGGER.error(f"AI SEO generation failed: {e}")
        events.append(WorkflowEvent(step="copywrite", message=f"AI SEO failed: {str(e)}, using fallback"))
        return _fallback_seo_copy(product, normalized, events)


def _fallback_seo_copy(product: Dict[str, Any], normalized: Dict[str, Any], events: List[WorkflowEvent]) -> Dict[str, Any]:
    """Fallback SEO copy generation without AI."""
    key_attr = next(iter(normalized.values()), product.get("description", ""))
    title = f"{product['name']} | {product.get('category', '').title()}".strip()
    description = f"Buy {product['name']} featuring {key_attr if isinstance(key_attr, str) else product.get('description', '')}."
    keywords = sorted({product.get("category", ""), product.get("name", "")})
    events.append(WorkflowEvent(step="copywrite", message="Generated SEO copy"))
    return {"title": title, "description": description.strip(), "keywords": [kw for kw in keywords if kw]}


def _localize_copy(seo_copy: Dict[str, Any], events: List[WorkflowEvent]) -> List[Dict[str, Any]]:
    client = _get_openai_client()
    if client:
        return _ai_localize_copy(seo_copy, events, client)
    else:
        events.append(WorkflowEvent(step="localize", message="Using fallback localization"))
        return _fallback_localize_copy(seo_copy, events)


def _ai_localize_copy(seo_copy: Dict[str, Any], events: List[WorkflowEvent], client) -> List[Dict[str, Any]]:
    """Use OpenAI to create localized versions of product copy."""
    target_locales = ["en-US", "es-ES", "fr-FR"]  # English, Spanish, French

    base_copy = {
        "title": seo_copy.get("title", ""),
        "description": seo_copy.get("description", ""),
        "long_description": seo_copy.get("long_description", "")
    }

    localizations = []

    # Add English version (base)
    localizations.append({
        "locale": "en-US",
        "title": base_copy["title"],
        "description": base_copy["description"],
        "long_description": base_copy.get("long_description", "")
    })

    # Generate other locales with AI
    for locale in target_locales[1:]:  # Skip en-US
        try:
            locale_name = {"es-ES": "Spanish", "fr-FR": "French"}.get(locale, locale)

            prompt = f"""
            Translate and localize this e-commerce product copy to {locale_name}.
            Adapt the content for {locale_name} market preferences and cultural context:

            Original Title: {base_copy['title']}
            Original Description: {base_copy['description']}
            Long Description: {base_copy.get('long_description', 'N/A')}

            Requirements:
            - Maintain SEO effectiveness
            - Adapt cultural references and selling points
            - Keep character limits similar to original
            - Use natural, native-sounding language
            - Preserve key product information

            Return JSON format:
            {{
                "title": "Translated title",
                "description": "Translated description",
                "long_description": "Translated long description"
            }}
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are an expert translator and localizer specializing in e-commerce copy for {locale_name} markets. Provide culturally appropriate, SEO-optimized translations. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )

            import json as json_lib
            translated = json_lib.loads(response.choices[0].message.content)

            localizations.append({
                "locale": locale,
                "title": translated.get("title", ""),
                "description": translated.get("description", ""),
                "long_description": translated.get("long_description", "")
            })

            events.append(WorkflowEvent(step="localize", message=f"AI localized to {locale_name}", payload={"token_usage": response.usage.total_tokens}))

        except Exception as e:
            LOGGER.error(f"AI localization failed for {locale}: {e}")
            events.append(WorkflowEvent(step="localize", message=f"Localization failed for {locale}: {str(e)}"))

    return localizations


def _fallback_localize_copy(seo_copy: Dict[str, Any], events: List[WorkflowEvent]) -> List[Dict[str, Any]]:
    """Fallback localization without AI."""
    events.append(WorkflowEvent(step="localize", message="Generated default locale copy"))
    return [{"locale": "en-US", "title": seo_copy.get("title", ""), "description": seo_copy.get("description", "")}]


def _run_sequential_pipeline(product: Dict[str, Any]) -> EnrichmentState:
    events: List[WorkflowEvent] = []
    state: EnrichmentState = {"product": product, "events": events}
    _node_ingest(state)
    state.update(_node_extract(state))
    state.update(_node_validate(state))
    state.update(_node_copywrite(state))
    state.update(_node_localize(state))
    state.update(_node_publish(state))
    return state


def enrich_product(product: Dict[str, Any]) -> ProcessedProduct:
    start_time = time.time()
    sku = product.get("sku", "UNKNOWN")

    if LANGGRAPH_AVAILABLE:
        LOGGER.info(f"[LangGraph] Starting enrichment for SKU: {sku}")
        langsmith_configured = os.getenv("LANGSMITH_API_KEY") is not None
        if langsmith_configured:
            LOGGER.info(f"[LangSmith] Tracing enabled for SKU: {sku}")

        graph = _get_graph()
        state: EnrichmentState = {
            "product": product,
            "events": [],
        }

        # Run with LangSmith tracing if configured
        if langsmith_configured and langsmith is not None:
            # Use run_name for better trace identification
            run_name = f"enrich_product_{sku}_{int(time.time())}"
            result: EnrichmentState = graph.invoke(
                state,
                config={"run_name": run_name, "metadata": {"sku": sku}}
            )  # type: ignore[attr-defined]
        else:
            result: EnrichmentState = graph.invoke(state)  # type: ignore[attr-defined]

        duration = time.time() - start_time
        LOGGER.info(f"[LangGraph] Completed enrichment for SKU: {sku} in {duration:.2f}s")
    else:
        LOGGER.info(f"[Sequential] Starting enrichment for SKU: {sku}")
        result = _run_sequential_pipeline(product)
        duration = time.time() - start_time
        LOGGER.info(f"[Sequential] Completed enrichment for SKU: {sku} in {duration:.2f}s")

    events = result.get("events", [])
    enriched = result.get("enriched")
    if not enriched:
        raise RuntimeError("Enrichment failed to produce output")

    return ProcessedProduct(
        sku=product["sku"],
        original=product,
        enriched=enriched,
        events=events,
    )


def process_pending_products(simple_path: str, enriched_path: str, *, process_all: bool = False) -> List[ProcessedProduct]:
    """Load catalog files, process new products, and persist enriched results."""
    simple_records = load_json_array(Path(simple_path))
    enriched_records = load_json_array(Path(enriched_path))

    existing_skus = {record.get("sku") for record in enriched_records}
    pending = [record for record in simple_records if record.get("sku") not in existing_skus]
    if not process_all and pending:
        pending = [pending[-1]]

    processed: List[ProcessedProduct] = []
    for product in pending:
        try:
            result = enrich_product(product)
            processed.append(result)
            LOGGER.info("Processed product %s", result.sku)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to process product %s: %s", product.get("sku"), exc)

    if processed:
        append_unique_records(
            Path(enriched_path),
            existing=enriched_records,
            new_records=(result.enriched for result in processed),
            key="sku",
        )
    return processed

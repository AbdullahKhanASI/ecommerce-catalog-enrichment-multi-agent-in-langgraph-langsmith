import { ChangeEvent, FormEvent, useState, useEffect } from 'react';

type WorkflowEvent = {
  step: string;
  message: string;
  timestamp: string;
};

type StreamMessage =
  | { type: 'ack'; product: any }
  | { type: 'workflow'; steps: string[] }
  | { type: 'event'; sku: string; event: WorkflowEvent }
  | { type: 'enriched'; sku: string; enriched: any }
  | { type: 'done'; count: number }
  | { type: 'complete'; exitCode: number | null }
  | { type: 'stderr'; data: string }
  | { type: 'log'; data: string }
  | { type: string; [key: string]: any };

type FormState = {
  sku: string;
  name: string;
  description: string;
  category: string;
  price: string;
  currency: string;
  attributesInput: string;
};

const initialForm: FormState = {
  sku: '',
  name: '',
  description: '',
  category: '',
  price: '',
  currency: 'USD',
  attributesInput: `{
  "color": "",
  "material": ""
}`,
};

export default function HomePage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [originalProduct, setOriginalProduct] = useState<any | null>(null);
  const [enrichedProduct, setEnrichedProduct] = useState<any | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [workflowSteps, setWorkflowSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (key: keyof FormState) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const resetState = () => {
    setOriginalProduct(null);
    setEnrichedProduct(null);
    setEvents([]);
    setLogLines([]);
    setWorkflowSteps([]);
    setCurrentStep(null);
    setCompletedSteps(new Set());
    setProgress(0);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    resetState();

    // Immediately show the submitted product
    const submittedProduct = {
      sku: form.sku,
      name: form.name,
      description: form.description,
      category: form.category,
      price: parseFloat(form.price) || 0,
      currency: form.currency,
      attributes: JSON.parse(form.attributesInput || '{}')
    };
    setOriginalProduct(submittedProduct);

    try {
      const response = await fetch('/api/enrich', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(form),
      });

      if (!response.ok || !response.body) {
        const text = await response.text();
        throw new Error(text || `Request failed with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });

        // Process Server-Sent Events format (data: {...}\n\n)
        let eventEndIndex: number;
        while ((eventEndIndex = buffer.indexOf('\n\n')) >= 0) {
          const eventChunk = buffer.slice(0, eventEndIndex).trim();
          buffer = buffer.slice(eventEndIndex + 2);

          if (eventChunk.startsWith('data: ')) {
            const jsonData = eventChunk.slice(6); // Remove 'data: ' prefix
            if (!jsonData) continue;
            try {
              const data: StreamMessage = JSON.parse(jsonData);
              handleStreamMessage(data);
            } catch (err) {
              setLogLines((prev) => [...prev, jsonData]);
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Unexpected error.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStreamMessage = (message: StreamMessage) => {
    switch (message.type) {
      case 'ack':
        setOriginalProduct(message.product);
        break;
      case 'workflow':
        setWorkflowSteps(message.steps);
        // Initialize progress tracking
        setProgress(0);
        setCompletedSteps(new Set());
        setCurrentStep(null);
        break;
      case 'event':
        if ((message as any).event) {
          const event = (message as any).event;
          setEvents((prev) => [...prev, event]);
          setCurrentStep(event.step);

          // Update completed steps and progress
          // Detect step completion based on actual backend messages
          const isStepCompleted = (() => {
            const msg = event.message.toLowerCase();
            switch (event.step) {
              case 'ingest':
                return msg.includes('loaded product');
              case 'extract':
                return msg.includes('ai extracted') || msg.includes('extracted product attributes');
              case 'validate':
                return msg.includes('validation passed');
              case 'copywrite':
                return msg.includes('ai generated seo') || msg.includes('generated seo copy');
              case 'localize':
                return msg.includes('ai localized') || msg.includes('localized to');
              case 'publish':
                return msg.includes('enriched product ready');
              default:
                return false;
            }
          })();

          if (isStepCompleted) {
            setCompletedSteps(prev => {
              const newCompleted = new Set(prev);
              newCompleted.add(event.step);
              // Calculate progress based on current workflow steps
              setWorkflowSteps(currentSteps => {
                if (currentSteps.length > 0) {
                  const progressPercent = (newCompleted.size / currentSteps.length) * 100;
                  setProgress(progressPercent);
                }
                return currentSteps;
              });
              return newCompleted;
            });
          }
        }
        break;
      case 'enriched':
        setEnrichedProduct(message.enriched);
        // Don't auto-complete all steps - let individual events handle completion
        setCurrentStep(null); // Clear current step since workflow is done
        break;
      case 'stderr':
      case 'log':
        if (message.data) {
          setLogLines((prev) => [...prev, String(message.data)]);
        }
        break;
      case 'complete':
        setLogLines((prev) => [...prev, `Process exited with code ${message.exitCode}`]);
        // Clear current step - individual step completion should handle the rest
        setCurrentStep(null);
        break;
      default:
        break;
    }
  };

  return (
    <main>
      <section className="hero">
        <div className="hero-content">
          <h1>🚀 AI Catalog Enrichment</h1>
          <p>Transform your products with intelligent multi-agent enrichment powered by LangGraph and OpenAI</p>
          {isSubmitting && (
            <div className="global-progress">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <span className="progress-text">{Math.round(progress)}% Complete</span>
            </div>
          )}
        </div>
      </section>

      <section>
        <h2>Add Product</h2>
        <form onSubmit={handleSubmit}>
          <label>
            SKU
            <input value={form.sku} onChange={handleChange('sku')} placeholder="SKU-1234" required />
          </label>
          <label>
            Name
            <input value={form.name} onChange={handleChange('name')} placeholder="Product name" required />
          </label>
          <label>
            Description
            <textarea value={form.description} onChange={handleChange('description')} placeholder="Product description" required />
          </label>
          <label>
            Category
            <input value={form.category} onChange={handleChange('category')} placeholder="Category" />
          </label>
          <label>
            Price
            <input type="number" step="0.01" value={form.price} onChange={handleChange('price')} placeholder="0.00" />
          </label>
          <label>
            Currency
            <input value={form.currency} onChange={handleChange('currency')} placeholder="USD" />
          </label>
          <label>
            Attributes (JSON)
            <textarea value={form.attributesInput} onChange={handleChange('attributesInput')} />
          </label>
          <button type="submit" disabled={isSubmitting} className={isSubmitting ? 'loading' : ''}>
            {isSubmitting ? (
              <>
                <div className="spinner"></div>
                <span>Enriching Product...</span>
              </>
            ) : (
              '🎯 Enrich Product'
            )}
          </button>
        </form>
        {error && <p style={{ color: '#dc2626' }}>{error}</p>}
      </section>

      <section className="workflow-section">
        <h2>🔄 Workflow Progress</h2>
        {workflowSteps.length > 0 && (
          <div className="workflow-steps">
            {workflowSteps.map((step) => {
              const isCompleted = completedSteps.has(step);
              const isCurrent = currentStep === step;

              return (
                <div key={step} className={`workflow-step ${isCompleted ? 'completed' : isCurrent ? 'active' : 'pending'}`}>
                  <div className="step-indicator">
                    {isCompleted ? '✅' : isCurrent ? <div className="step-spinner"></div> : '⏳'}
                  </div>
                  <div className="step-content">
                    <div className="step-name">{step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                    {isCurrent && <div className="step-pulse">Processing...</div>}
                    {isCompleted && <div className="step-status">✓ Complete</div>}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {events.length > 0 && (
          <div className="events-container">
            <h3>📋 Activity Log</h3>
            <div className="status-stream">
              <ul>
                {events.slice(-10).map((event, idx) => (
                  <li key={`${event.step}-${idx}`} className="event-item">
                    <span className="event-timestamp">
                      [{new Date(event.timestamp).toLocaleTimeString()}]
                    </span>
                    <span className="event-step">{event.step}:</span>
                    <span className="event-message">{event.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {logLines.length > 0 && (
          <details className="logs-details">
            <summary>🔍 Technical Logs</summary>
            <pre className="logs-content">{logLines.join('\n')}</pre>
          </details>
        )}
      </section>

      <section>
        <h2>📊 Results</h2>
        <div className="card-grid">
          <div className="card original-card">
            <h3>📝 Original Product</h3>
            {originalProduct ? (
              <div className="json-viewer">
                <pre>{JSON.stringify(originalProduct, null, 2)}</pre>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📦</div>
                <p>Submit a product to get started</p>
              </div>
            )}
          </div>
          <div className="card enriched-card">
            <h3>✨ AI-Enhanced Product</h3>
            {enrichedProduct ? (
              <div className="json-viewer enriched-content">
                <div className="enhancement-badge">🎯 AI Enhanced</div>
                <pre>{JSON.stringify(enrichedProduct, null, 2)}</pre>
              </div>
            ) : isSubmitting ? (
              <div className="loading-state">
                <div className="loading-animation">
                  <div className="loading-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
                <p>AI agents are enriching your product...</p>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">🤖</div>
                <p>Waiting for AI enrichment...</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

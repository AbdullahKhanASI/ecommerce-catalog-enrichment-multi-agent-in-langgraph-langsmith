import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const body = req.body;

  if (!body || !body.sku || !body.name || !body.description) {
    return res.status(400).json({ error: 'Missing required fields (sku, name, description).' });
  }

  let attributes: Record<string, unknown> | undefined = body.attributes;
  if (!attributes && body.attributesInput) {
    try {
      attributes = JSON.parse(body.attributesInput);
    } catch (err) {
      return res.status(400).json({ error: 'Invalid attributes JSON.' });
    }
  }

  const product = {
    sku: body.sku,
    name: body.name,
    description: body.description,
    category: body.category || 'general',
    price: typeof body.price === 'number' ? body.price : Number(body.price) || 0,
    currency: body.currency || 'USD',
    attributes: attributes || {},
  };

  try {
    // Forward request to FastAPI backend
    const response = await fetch('http://localhost:8000/api/enrich/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(product),
    });

    if (!response.ok) {
      throw new Error(`FastAPI error: ${response.status}`);
    }

    // Set up streaming response
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Stream the response from FastAPI
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        res.write(chunk);
      }
    } finally {
      reader.releaseLock();
      res.end();
    }

  } catch (error) {
    console.error('Error forwarding to FastAPI:', error);
    res.status(500).json({ error: `Failed to process request: ${error.message}` });
  }
}

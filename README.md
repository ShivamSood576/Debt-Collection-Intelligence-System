# Contract Analysis API - RAG-Powered System

A production-ready FastAPI application for contract analysis using RAG (Retrieval-Augmented Generation), LLM-powered field extraction, risk auditing, and real-time streaming responses.

## 🚀 Features

- **PDF Ingestion**: Upload and process multiple PDF contracts with automatic chunking and vector embedding
- **Field Extraction**: AI-powered extraction of 11+ structured contract fields
- **RAG Question Answering**: Ask questions grounded in actual document content with citations
- **Risk Auditing**: Detect 8 categories of risky clauses with severity scoring
- **Real-time Streaming**: Server-Sent Events (SSE) for ChatGPT-like streaming responses
- **Admin APIs**: Health checks, metrics tracking, document listing

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Example Usage](#example-usage)
- [Architecture](#architecture)
- [Trade-offs & Design Decisions](#trade-offs--design-decisions)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)

---

## 🏁 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- 2GB+ disk space (for vector database)

### Local Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd contract-analysis-api
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables**
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"

# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"
```

5. **Run the server**
```bash
python last_phase_app_api.py

# OR using uvicorn
uvicorn last_phase_app_api:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the API**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API: http://localhost:8000/

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for embeddings and LLM calls |
| `CHROMA_DIR` | No | `./chroma_store` | Directory for Chroma vector database |
| `UPLOAD_DIR` | No | `./uploaded_contracts` | Directory for uploaded PDF files |
| `METADATA_DIR` | No | `./contract_metadata` | Directory for document metadata JSON files |

**Setting environment variables:**

```bash
# Method 1: Export in terminal
export OPENAI_API_KEY="sk-proj-xxxxx"

# Method 2: Create .env file (recommended)
# Create a file named .env in the project root:
OPENAI_API_KEY=sk-proj-xxxxx

# Method 3: Set in code (NOT recommended for production)
# Edit last_phase_app_api.py line 24
```

---

<img width="1799" height="622" alt="image" src="https://github.com/user-attachments/assets/1f04e6d8-c37e-4300-8b15-4e0804f7c2c5" />


## 📡 API Endpoints

### 1. POST `/ingest` - Upload & Process Contracts

**Description**: Upload 1-N PDF contracts, extract text, chunk, embed, and store in vector database.

**Request**:
```bash
# Windows PowerShell
curl.exe -X POST "http://localhost:8000/ingest" `
  -H "accept: application/json" `
  -F "files=@contract1.pdf" `
  -F "files=@contract2.pdf"

# Linux/Mac/Git Bash
curl -X POST "http://localhost:8000/ingest" \
  -H "accept: application/json" \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf"
```

**Response**:
```json
{
  "document_ids": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "b2c3d4e5-f6a7-8901-bcde-f12345678901"
  ],
  "message": "Successfully ingested 2 document(s)",
  "total_chunks": 142
}
```

---

### 2. POST `/extract` - Extract Contract Fields

**Description**: Extract 11 structured fields from an ingested contract.

**Request**:
```bash
# PowerShell
curl.exe -X POST "http://localhost:8000/extract" `
  -H "Content-Type: application/json" `
  -d '{\"document_id\": \"a1b2c3d4-e5f6-7890-abcd-ef1234567890\"}'

# Bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}'
```

**Response**:
```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "fields": {
    "parties": ["Acme Corporation", "Beta Industries LLC"],
    "effective_date": "2024-01-15",
    "term": "24 months",
    "governing_law": "Delaware",
    "payment_terms": "Net 30 days from invoice date",
    "termination": "Either party may terminate with 30 days written notice",
    "auto_renewal": "Automatically renews for successive 12-month terms unless notice given 60 days prior",
    "confidentiality": "Both parties agree to maintain confidentiality for 3 years post-termination",
    "indemnity": "Each party indemnifies the other for third-party claims arising from their breach",
    "liability_cap": {
      "amount": 1000000,
      "currency": "USD"
    },
    "signatories": [
      {"name": "John Smith", "title": "CEO"},
      {"name": "Jane Doe", "title": "VP Operations"}
    ]
  }
}
```

---

### 3. POST `/ask` - Ask Questions (RAG)

**Description**: Ask questions about contracts using RAG. Returns answers grounded in documents with citations.

**Request**:
```bash
# PowerShell
curl.exe -X POST "http://localhost:8000/ask" `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"What is the payment term?\", \"k\": 3}'

# With document filtering
curl.exe -X POST "http://localhost:8000/ask" `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"What is the payment term?\", \"document_ids\": [\"a1b2c3d4-e5f6-7890-abcd-ef1234567890\"], \"k\": 3}'

# Bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the payment term?", "k": 3}'
```

**Response**:
```json
{
  "question": "What is the payment term?",
  "answer": "According to Section 5.2, payment is due net 30 days from invoice date. Late payments incur 1.5% monthly interest. An early payment discount of 2% is available if paid within 10 days.",
  "citations": [
    {
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "page": 5,
      "content": "Section 5.2 Payment Terms. All payments shall be made within thirty (30) days from invoice date..."
    },
    {
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "page": 5,
      "content": "Invoices will be sent monthly. Late payments incur 1.5% interest per month..."
    }
  ]
}
```

---

### 4. GET `/ask/stream` - Stream Answers (SSE)

**Description**: Stream answer tokens in real-time using Server-Sent Events.

**Request**:
```bash
# PowerShell
curl.exe "http://localhost:8000/ask/stream?question=What%20is%20the%20governing%20law?&k=3"

# Bash
curl "http://localhost:8000/ask/stream?question=What%20is%20the%20governing%20law?&k=3"
```

**JavaScript Client Example**:
```javascript
const eventSource = new EventSource(
  '/ask/stream?question=What is the governing law?&k=3'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'citations') {
    console.log('Citations:', data.content);
  } else if (data.type === 'token') {
    process.stdout.write(data.content);
  } else if (data.type === 'done') {
    console.log('\nComplete!');
    eventSource.close();
  }
};
```

**Response Stream**:
```
data: {"type":"citations","content":[{"document_id":"abc","page":12,"content":"..."}]}

data: {"type":"token","content":"According"}

data: {"type":"token","content":" to"}

data: {"type":"token","content":" Section"}

...

data: {"type":"done","content":""}
```

---

### 5. POST `/audit` - Detect Risky Clauses

**Description**: Audit contract for 8 categories of risky clauses.

**Request**:
```bash
# PowerShell
curl.exe -X POST "http://localhost:8000/audit" `
  -H "Content-Type: application/json" `
  -d '{\"document_id\": \"a1b2c3d4-e5f6-7890-abcd-ef1234567890\"}'

# Bash
curl -X POST "http://localhost:8000/audit" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}'
```

**Response**:
```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "total_risks": 3,
  "findings": [
    {
      "risk_type": "AUTO_RENEWAL_SHORT_NOTICE",
      "severity": "high",
      "description": "Contract auto-renews with only 15 days notice required",
      "evidence": "Section 8.1: This Agreement automatically renews for successive one-year terms unless either party provides written notice of non-renewal at least fifteen (15) days prior...",
      "recommendation": "Negotiate for minimum 30-60 days notice period to allow adequate time for review and decision-making."
    },
    {
      "risk_type": "UNLIMITED_LIABILITY",
      "severity": "high",
      "description": "No cap on liability exposure",
      "evidence": "Section 10.3: Each party shall be liable for all damages, losses, and expenses arising from any breach of this Agreement, without limitation as to amount...",
      "recommendation": "Add reasonable liability cap, typically 12 months of fees or $1,000,000, whichever is greater. Exclude consequential damages."
    },
    {
      "risk_type": "BROAD_INDEMNITY",
      "severity": "medium",
      "description": "Overly broad indemnification including consequential damages",
      "evidence": "Section 11.2: Company agrees to indemnify, defend, and hold harmless Provider from any and all claims, including consequential, indirect, and punitive damages...",
      "recommendation": "Limit indemnity to direct damages caused by your breach. Exclude consequential and punitive damages."
    }
  ],
  "audit_date": "2024-11-26T10:30:00.123456"
}
```

---

### 6. GET `/documents` - List Documents

**Description**: List all ingested documents with metadata.

**Request**:
```bash
# PowerShell
curl.exe http://localhost:8000/documents

# Bash
curl http://localhost:8000/documents
```

**Response**:
```json
{
  "documents": [
    {
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "filename": "contract1.pdf",
      "upload_date": "2024-11-26T09:15:30.123456",
      "num_pages": 25,
      "num_chunks": 67
    }
  ],
  "total": 1
}
```

---

### 7. GET `/healthz` - Health Check

**Description**: Check server health and uptime.

**Request**:
```bash
curl http://localhost:8000/healthz
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-11-26T10:45:00.123456",
  "uptime_seconds": 3245.67
}
```

---

### 8. GET `/metrics` - Usage Metrics

**Description**: Get API usage statistics.

**Request**:
```bash
curl http://localhost:8000/metrics
```

**Response**:
```json
{
  "total_documents": 15,
  "total_ingestions": 8,
  "total_extractions": 12,
  "total_questions": 143,
  "total_audits": 7
}
```

---

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌────────────────────────────────────┐
│      FastAPI Application           │
│  • Pydantic validation             │
│  • Async endpoints                 │
│  • Auto-generated OpenAPI docs     │
└──────┬─────────────────────────────┘
       │
       ↓
┌────────────────────────────────────┐
│    Business Logic Layer            │
│  • PDF Processing (PyPDF)          │
│  • Text Chunking (LangChain)       │
│  • RAG Pipeline                    │
│  • Streaming Engine (SSE)          │
└──────┬─────────────────────────────┘
       │
       ↓
┌──────────────────┐  ┌──────────────┐
│  Chroma Vector   │  │  OpenAI API  │
│  Database        │  │  • GPT-4o-   │
│  • HNSW Index    │  │    mini      │
│  • 1536D vectors │  │  • ada-002   │
└──────────────────┘  └──────────────┘
```

See [DESIGN.md](DESIGN.md) for detailed architecture documentation.

---

## ⚖️ Trade-offs & Design Decisions

### 1. **GPT-4o-mini vs GPT-4**

**Choice**: GPT-4o-mini

**Rationale**:
- 15x cheaper ($0.002 vs $0.03 per 1K tokens)
- 2-3x faster response times
- 90% quality of GPT-4 (sufficient for contract analysis)
- Better for high-volume production use

**Trade-off**: Slightly lower accuracy on complex legal reasoning

---

### 2. **Chroma vs Pinecone/Weaviate**

**Choice**: Chroma (local)

**Rationale**:
- Free and open-source
- Data privacy (no external service)
- Easy setup (pip install)
- Sufficient for <1M documents

**Trade-off**: Limited scalability compared to managed services

**Migration Path**: For >1M documents, switch to Pinecone/Weaviate with minimal code changes

---

### 3. **Chunk Size: 1000 chars with 200 overlap**

**Choice**: 1000 characters, 200 overlap

**Rationale**:
- Balances precision and context
- Standard for legal documents
- Prevents information loss at boundaries
- Optimal for 1536D embeddings

**Trade-off**: More chunks = higher storage (but better retrieval quality)

---

### 4. **RAG vs Fine-tuning**

**Choice**: RAG (Retrieval-Augmented Generation)

**Rationale**:
- Instant updates (no retraining)
- Cites sources (explainability)
- Cheaper than fine-tuning
- Scales to unlimited documents

**Trade-off**: Slightly slower than pure LLM (retrieval step)

---

### 5. **Streaming (SSE) vs Batch**

**Choice**: Server-Sent Events for streaming

**Rationale**:
- 80% reduction in perceived latency
- Better UX (immediate feedback)
- Built-in browser support (EventSource)
- Allows early response cancellation

**Trade-off**: More complex implementation, harder to cache

---

### 6. **In-Memory Metrics vs Database**

**Choice**: In-memory dictionary

**Rationale**:
- Simple implementation
- No external dependencies
- Sufficient for MVP/demo

**Trade-off**: Resets on server restart

**Production Alternative**: Use Redis or PostgreSQL for persistent metrics

---

### 7. **Pydantic Validation**

**Choice**: Strict type validation with Pydantic

**Rationale**:
- Type safety at runtime
- Automatic API documentation
- Input validation
- Clear error messages

**Trade-off**: Slightly more verbose code

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Test Streaming Endpoint
```bash
# HTML Client
python -m http.server 8080
# Open: http://localhost:8080/test_streaming.html

# Python Client
python test_streaming.py
```

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t contract-analysis-api .
```

### Run Container
```bash
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-your-key" \
  -v $(pwd)/chroma_store:/app/chroma_store \
  -v $(pwd)/uploaded_contracts:/app/uploaded_contracts \
  --name contract-api \
  contract-analysis-api
```

### Docker Compose
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

---

## 📊 Performance

- **Ingestion**: ~2-5 seconds per PDF (20-50 pages)
- **Extraction**: ~3-8 seconds per document
- **RAG Query**: ~2-4 seconds (batch), ~0.5s first token (streaming)
- **Audit**: ~5-12 seconds per document
- **Throughput**: ~100 requests/minute (single instance)

**Scaling**:
- Horizontal: Run multiple instances behind load balancer
- Vertical: Increase OpenAI rate limits
- Caching: Add Redis for frequently asked questions

---

## 🔒 Security Notes

⚠️ **Important**: This is a demo/MVP. For production:

1. **Remove hardcoded API key** (line 24 in `last_phase_app_api.py`)
2. Add authentication (JWT, OAuth2)
3. Add rate limiting (slowapi, nginx)
4. Add input sanitization
5. Use HTTPS/TLS
6. Implement CORS properly
7. Add logging and monitoring
8. Use secrets management (AWS Secrets Manager, HashiCorp Vault)

---

## 📚 Additional Documentation

- [DESIGN.md](DESIGN.md) - Architecture deep dive
- [AI_THEORY_EXPLAINED.md](AI_THEORY_EXPLAINED.md) - AI concepts explained
- [COMPLETE_API_DOCUMENTATION.md](COMPLETE_API_DOCUMENTATION.md) - Full API reference
- [prompts/](prompts/) - LLM prompts used in the system
- [eval/](eval/) - Evaluation set and scoring

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - see LICENSE file

---

## 🙋 Support

For questions or issues:
- Open an issue on GitHub
- Email: your-email@example.com

---

## 🎯 Roadmap

- [ ] Add support for DOCX, TXT files
- [ ] Multi-language support
- [ ] Batch processing API
- [ ] Export to JSON/CSV
- [ ] Webhook notifications
- [ ] GraphQL API
- [ ] Web UI dashboard

---

**Built with** ❤️ **using FastAPI, LangChain, OpenAI, and Chroma**


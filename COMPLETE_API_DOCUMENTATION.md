# 📄 Contract Analysis API - Complete Documentation

## 🎯 Overview

A production-ready FastAPI application for intelligent contract analysis featuring:
- Multi-PDF document ingestion
- AI-powered field extraction
- RAG-based question answering
- Real-time streaming responses
- Risk detection and auditing
- Health monitoring and metrics

**Technology Stack:**
- Framework: FastAPI
- LLM: OpenAI GPT-4o-mini
- Vector Database: Chroma
- PDF Parser: LangChain + PyPDF
- Streaming: Server-Sent Events (SSE)

---

## 📋 Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Usage Examples](#usage-examples)
6. [Architecture](#architecture)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Testing](#testing)
10. [Deployment](#deployment)

---

## 🚀 Installation

### Prerequisites
```bash
Python 3.8+
OpenAI API Key
```

### Install Dependencies
```powershell
pip install fastapi uvicorn langchain langchain-openai langchain-community openai tiktoken pypdf python-multipart
```

### Set API Key
Update line 24 in `last_phase_app_api.py`:
```python
OPENAI_API_KEY = "your-api-key-here"
```

---

## ⚡ Quick Start

### Start Server
```powershell
# Option 1: Direct Python
python last_phase_app_api.py

# Option 2: Uvicorn with auto-reload
uvicorn last_phase_app_api:app --reload --port 8000
```

### Access Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000/

---

## 🔌 API Endpoints

### 1. POST /ingest - Document Ingestion

**Purpose:** Upload and process PDF contracts into the system.

**Request:**
```http
POST /ingest
Content-Type: multipart/form-data

files: [file1.pdf, file2.pdf, ...]
```

**Response:**
```json
{
  "document_ids": [
    "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "7c8d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
  ],
  "message": "Successfully ingested 2 document(s)",
  "total_chunks": 156
}
```

**Process Flow:**
1. Validate PDF files
2. Generate unique document_id (UUID)
3. Save uploaded file to `uploaded_contracts/`
4. Extract text and split into chunks
5. Create vector embeddings
6. Store in Chroma vector database
7. Save metadata to `contract_metadata/{document_id}.json`
8. Return document_ids for future reference

**Configuration:**
- Chunk size: 1000 characters
- Chunk overlap: 200 characters
- Storage: Local filesystem

**Example (PowerShell):**
```powershell
curl.exe -X POST http://localhost:8000/ingest `
  -F "files=@contract1.pdf" `
  -F "files=@contract2.pdf"
```

---

### 2. POST /extract - Field Extraction

**Purpose:** Extract structured contract data using AI.

**Request:**
```http
POST /extract
Content-Type: application/json

{
  "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

**Response:**
```json
{
  "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "fields": {
    "parties": [
      "Acme Corporation",
      "Beta Industries LLC"
    ],
    "effective_date": "2024-01-15",
    "term": "24 months with option to renew",
    "governing_law": "State of Delaware",
    "payment_terms": "Net 30 days from invoice date",
    "termination": "Either party may terminate with 60 days written notice",
    "auto_renewal": "Automatically renews for successive 12-month periods",
    "confidentiality": "Obligations survive for 5 years post-termination",
    "indemnity": "Mutual indemnification for third-party claims",
    "liability_cap": {
      "amount": 1000000,
      "currency": "USD"
    },
    "signatories": [
      {
        "name": "John Smith",
        "title": "Chief Executive Officer"
      },
      {
        "name": "Jane Doe",
        "title": "Chief Financial Officer"
      }
    ]
  }
}
```

**Extracted Fields:**

| Field | Type | Description |
|-------|------|-------------|
| parties | string[] | All contracting parties |
| effective_date | string | Contract start date |
| term | string | Contract duration |
| governing_law | string | Jurisdiction |
| payment_terms | string | Payment conditions |
| termination | string | How to end contract |
| auto_renewal | string | Renewal terms |
| confidentiality | string | Confidentiality provisions |
| indemnity | string | Indemnification clauses |
| liability_cap | object | Max liability (amount + currency) |
| signatories | object[] | Signers (name + title) |

**AI Process:**
1. Load full contract text (limited to 8000 chars)
2. Use GPT-4o-mini with structured prompt
3. Parse JSON response
4. Validate against Pydantic models
5. Save to metadata file

**Example (PowerShell):**
```powershell
$body = @{document_id="your-doc-id"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/extract `
  -Method POST -Body $body -ContentType "application/json"
```

---

### 3. POST /ask - Question Answering (RAG)

**Purpose:** Ask questions about contracts with AI-generated answers grounded in document content.

**Request:**
```http
POST /ask
Content-Type: application/json

{
  "question": "What is the governing law?",
  "document_ids": ["3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"],
  "k": 3
}
```

**Response:**
```json
{
  "question": "What is the governing law?",
  "answer": "According to Section 12.3 of the agreement, this contract shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law provisions.",
  "citations": [
    {
      "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "page": 15,
      "content": "12.3 Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, excluding its conflicts of law rules..."
    },
    {
      "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "page": 15,
      "content": "Any disputes arising under this Agreement shall be resolved in the courts of Delaware..."
    }
  ]
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| question | string | Yes | - | Question to ask |
| document_ids | string[] | No | null | Filter by specific documents |
| k | integer | No | 3 | Number of relevant chunks (1-10) |

**RAG Process:**
1. Convert question to embedding
2. Search vector database for similar chunks
3. Filter by document_ids if specified
4. Build context from top k chunks
5. Send to LLM with strict grounding instructions
6. Return answer with source citations

**Example (PowerShell):**
```powershell
$body = @{
    question = "What are the payment terms?"
    k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/ask `
  -Method POST -Body $body -ContentType "application/json"
```

---

### 4. GET /ask/stream - Streaming Answers (SSE)

**Purpose:** Stream AI responses in real-time, token by token.

**Request:**
```http
GET /ask/stream?question=What%20is%20the%20term?&k=3&document_ids=doc-id-1
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| question | string | Yes | - | Question to ask |
| document_ids | string | No | null | Comma-separated doc IDs |
| k | integer | No | 3 | Number of chunks (1-10) |

**Response (Server-Sent Events):**
```
data: {"type":"citations","content":[{...}]}

data: {"type":"token","content":"The"}

data: {"type":"token","content":" contract"}

data: {"type":"token","content":" term"}

data: {"type":"token","content":" is"}

data: {"type":"done","content":""}
```

**Message Types:**

| Type | Description | When |
|------|-------------|------|
| `citations` | Source documents | First message |
| `token` | Single word/piece | During generation |
| `done` | Completion signal | Last message |
| `error` | Error message | On failure |

**JavaScript Example:**
```javascript
const eventSource = new EventSource(
  '/ask/stream?question=What is the term?&k=3'
);

let answer = '';

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'citations') {
    console.log('Sources:', data.content);
  } else if (data.type === 'token') {
    answer += data.content;
    document.getElementById('answer').textContent = answer;
  } else if (data.type === 'done') {
    console.log('Complete!');
    eventSource.close();
  }
};
```

**PowerShell Example:**
```powershell
curl.exe "http://localhost:8000/ask/stream?question=What%20is%20the%20term?&k=3"
```

**Features:**
- ✅ Real-time streaming
- ✅ Citations included
- ✅ Auto-scrolling UI support
- ✅ Error handling
- ✅ Cancelable streams

---

### 5. POST /audit - Risk Detection

**Purpose:** Identify risky contract clauses using AI analysis.

**Request:**
```http
POST /audit
Content-Type: application/json

{
  "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

**Response:**
```json
{
  "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "total_risks": 3,
  "audit_date": "2024-11-26T14:30:00.123456",
  "findings": [
    {
      "risk_type": "AUTO_RENEWAL_SHORT_NOTICE",
      "severity": "high",
      "description": "Contract automatically renews with only 15 days notice period, which is below the recommended 30 days minimum",
      "evidence": "Section 8.2: This Agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least fifteen (15) days prior to the end of the then-current term...",
      "recommendation": "Negotiate to extend notice period to at least 30 days to allow adequate time for decision-making and contract review"
    },
    {
      "risk_type": "UNLIMITED_LIABILITY",
      "severity": "high",
      "description": "No cap on liability for breaches, exposing company to unlimited financial risk",
      "evidence": "Section 10.1: Each party shall be liable for all damages, losses, and expenses arising from any breach of this Agreement, without limitation...",
      "recommendation": "Add a reasonable liability cap, typically 12 months of fees or $1,000,000, whichever is greater"
    },
    {
      "risk_type": "BROAD_INDEMNITY",
      "severity": "medium",
      "description": "Overly broad indemnification obligations that may include indirect damages",
      "evidence": "Section 11: Company agrees to indemnify, defend and hold harmless Provider from any and all claims, damages, liabilities, costs and expenses, including consequential damages...",
      "recommendation": "Limit indemnification to direct damages arising from gross negligence or willful misconduct"
    }
  ]
}
```

**Risk Categories:**

| Risk Type | Severity | Description |
|-----------|----------|-------------|
| AUTO_RENEWAL_SHORT_NOTICE | High | Auto-renewal with <30 days notice |
| UNLIMITED_LIABILITY | High | No cap on liability exposure |
| BROAD_INDEMNITY | Medium/High | Overly broad indemnification |
| UNFAVORABLE_TERMINATION | Medium | One-sided termination rights |
| ONE_SIDED_CONFIDENTIALITY | Medium | Unbalanced confidentiality |
| UNREASONABLE_PAYMENT | Medium | Unfavorable payment terms |
| UNILATERAL_CHANGES | High | Changes without consent |
| JURISDICTION_ISSUES | Low/Medium | Unfavorable jurisdiction |

**Risk Severity Levels:**
- **High**: Immediate attention required, significant financial/legal risk
- **Medium**: Should be negotiated, moderate risk
- **Low**: Minor concern, consider for negotiation

**AI Analysis:**
1. Load full contract text (up to 10,000 chars)
2. Use GPT-4o-mini with risk detection prompt
3. Identify clauses matching risk patterns
4. Extract evidence quotes
5. Classify severity
6. Generate recommendations
7. Save results to metadata

**Example (PowerShell):**
```powershell
$body = @{document_id="your-doc-id"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/audit `
  -Method POST -Body $body -ContentType "application/json"
```

---

### 6. GET /documents - List Documents

**Purpose:** Retrieve all ingested documents.

**Request:**
```http
GET /documents
```

**Response:**
```json
{
  "documents": [
    {
      "document_id": "3f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
      "filename": "Master-Services-Agreement.pdf",
      "upload_date": "2024-11-26T10:15:30.123456",
      "num_pages": 25,
      "num_chunks": 78
    },
    {
      "document_id": "7c8d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
      "filename": "NDA-Template.pdf",
      "upload_date": "2024-11-26T11:20:45.654321",
      "num_pages": 5,
      "num_chunks": 12
    }
  ],
  "total": 2
}
```

**Use Cases:**
- View all uploaded contracts
- Get document_ids for filtering
- Check ingestion history
- Monitor document library

---

### 7. GET /healthz - Health Check

**Purpose:** Monitor API health and uptime.

**Request:**
```http
GET /healthz
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-11-26T14:30:00.123456",
  "uptime_seconds": 3600.50
}
```

**Monitoring:**
- Use for load balancer health checks
- Monitor in production
- Track uptime metrics
- Detect service availability

---

### 8. GET /metrics - Usage Metrics

**Purpose:** Track API usage statistics.

**Request:**
```http
GET /metrics
```

**Response:**
```json
{
  "total_documents": 15,
  "total_ingestions": 20,
  "total_extractions": 45,
  "total_questions": 238,
  "total_audits": 18,
  "total_streams": 127
}
```

**Metrics Tracked:**

| Metric | Description |
|--------|-------------|
| total_documents | Number of docs in system |
| total_ingestions | API calls to /ingest |
| total_extractions | API calls to /extract |
| total_questions | API calls to /ask |
| total_audits | API calls to /audit |
| total_streams | API calls to /ask/stream |

**Use Cases:**
- Monitor API usage
- Track popular features
- Capacity planning
- Usage analytics

---

### 9. GET /docs - OpenAPI Documentation

**Purpose:** Interactive API documentation (auto-generated by FastAPI).

**Access:** http://localhost:8000/docs

**Features:**
- ✅ Try all endpoints interactively
- ✅ View request/response schemas
- ✅ Authentication testing
- ✅ Download OpenAPI spec
- ✅ Code generation support

**Alternative:** http://localhost:8000/redoc (ReDoc UI)

---

## 📊 Data Models

### Pydantic Models (Request/Response)

#### IngestResponse
```python
{
  "document_ids": List[str],
  "message": str,
  "total_chunks": int
}
```

#### ExtractRequest
```python
{
  "document_id": str
}
```

#### ExtractResponse
```python
{
  "document_id": str,
  "fields": ContractFields
}
```

#### ContractFields
```python
{
  "parties": List[str],
  "effective_date": Optional[str],
  "term": Optional[str],
  "governing_law": Optional[str],
  "payment_terms": Optional[str],
  "termination": Optional[str],
  "auto_renewal": Optional[str],
  "confidentiality": Optional[str],
  "indemnity": Optional[str],
  "liability_cap": Optional[LiabilityCap],
  "signatories": List[Signatory]
}
```

#### LiabilityCap
```python
{
  "amount": Optional[float],
  "currency": Optional[str]
}
```

#### Signatory
```python
{
  "name": str,
  "title": Optional[str]
}
```

#### AskRequest
```python
{
  "question": str,
  "document_ids": Optional[List[str]],
  "k": int  # default=3, min=1, max=10
}
```

#### AskResponse
```python
{
  "question": str,
  "answer": str,
  "citations": List[Citation]
}
```

#### Citation
```python
{
  "document_id": str,
  "page": Optional[int],
  "content": str
}
```

#### RiskFinding
```python
{
  "risk_type": str,
  "severity": str,  # "high", "medium", "low"
  "description": str,
  "evidence": str,
  "recommendation": Optional[str]
}
```

#### AuditRequest
```python
{
  "document_id": str
}
```

#### AuditResponse
```python
{
  "document_id": str,
  "total_risks": int,
  "findings": List[RiskFinding],
  "audit_date": str
}
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Application                     │
│  ┌───────────────────────────────────────────────┐ │
│  │  Endpoints (7)                                 │ │
│  │  • /ingest  • /extract  • /ask                │ │
│  │  • /ask/stream  • /audit  • /healthz          │ │
│  │  • /metrics                                    │ │
│  └───────────────────────────────────────────────┘ │
│                       │                              │
│  ┌───────────────────┴───────────────────────────┐ │
│  │  Core Services                                 │ │
│  │  • PDF Processing    • Text Chunking          │ │
│  │  • Vector Embeddings • LLM Integration        │ │
│  │  • Risk Analysis     • SSE Streaming          │ │
│  └─────────┬─────────────────────┬───────────────┘ │
└────────────┼─────────────────────┼──────────────────┘
             │                     │
      ┌──────▼─────┐        ┌─────▼──────┐
      │  Chroma    │        │  OpenAI    │
      │  Vector DB │        │  GPT-4o-   │
      │            │        │  mini      │
      └──────┬─────┘        └────────────┘
             │
      ┌──────▼────────────────────┐
      │  Local Storage            │
      │  • uploaded_contracts/    │
      │  • contract_metadata/     │
      │  • chroma_store/          │
      └───────────────────────────┘
```

### Data Flow

#### Ingestion Flow
```
PDF Upload → Validation → Text Extraction → Chunking →
Embedding Generation → Vector DB Storage → Metadata Save →
Return document_id
```

#### Question Answering Flow
```
Question → Embedding → Vector Search → Top K Chunks →
Context Building → LLM Query → Answer + Citations
```

#### Streaming Flow
```
Question → Vector Search → Citations (SSE) →
LLM Streaming → Tokens (SSE) → Done Signal (SSE)
```

---

## ⚙️ Configuration

### Environment Variables
```python
# In production, use environment variables:
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

### Directory Structure
```python
CHROMA_DIR = "./chroma_store"       # Vector database
UPLOAD_DIR = "./uploaded_contracts" # PDF files
METADATA_DIR = "./contract_metadata" # JSON metadata
```

### LLM Configuration
```python
# Model selection
ChatOpenAI(model="gpt-4o-mini")  # Fast, cost-effective
# ChatOpenAI(model="gpt-4")      # Higher quality

# Temperature
temperature=0  # Deterministic for extraction
streaming=True # For /ask/stream endpoint
```

### Chunking Configuration
```python
chunk_size=1000      # Characters per chunk
chunk_overlap=200    # Overlap for context
```

### RAG Configuration
```python
k=3  # Number of chunks to retrieve (adjustable 1-10)
```

---

## ❌ Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Document not found |
| 500 | Server Error | Internal error |

### Error Response Format
```json
{
  "detail": "Error message explaining what went wrong"
}
```

### Common Errors

#### 404: Document Not Found
```json
{
  "detail": "Document abc-123 not found"
}
```
**Solution:** Use `/documents` endpoint to get valid document_ids

#### 400: Invalid File Type
```json
{
  "detail": "File contract.docx is not a PDF"
}
```
**Solution:** Only upload PDF files

#### 500: LLM Error
```json
{
  "detail": "Error extracting fields: API rate limit exceeded"
}
```
**Solution:** Check OpenAI API key and rate limits

---

## 🧪 Testing

### Manual Testing

#### 1. Upload a Contract
```powershell
curl.exe -X POST http://localhost:8000/ingest `
  -F "files=@contract.pdf"
```

#### 2. Extract Fields
```powershell
$body = @{document_id="your-doc-id"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/extract `
  -Method POST -Body $body -ContentType "application/json"
```

#### 3. Ask a Question
```powershell
$body = @{question="What is the term?"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ask `
  -Method POST -Body $body -ContentType "application/json"
```

#### 4. Stream Answer
```powershell
curl.exe "http://localhost:8000/ask/stream?question=What%20is%20the%20term?"
```

#### 5. Run Audit
```powershell
$body = @{document_id="your-doc-id"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/audit `
  -Method POST -Body $body -ContentType "application/json"
```

#### 6. Check Health
```powershell
Invoke-RestMethod -Uri http://localhost:8000/healthz
```

### Interactive Testing
Visit: http://localhost:8000/docs

---

## 🚀 Deployment

### Local Development
```powershell
python last_phase_app_api.py
```

### Production with Uvicorn
```bash
uvicorn last_phase_app_api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

# Copy application
COPY last_phase_app_api.py .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "last_phase_app_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t contract-api .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key contract-api
```

### Cloud Deployment

#### AWS (Elastic Beanstalk)
```bash
eb init -p python-3.11 contract-api
eb create contract-api-env
eb deploy
```

#### Azure (App Service)
```bash
az webapp up --name contract-api --runtime "PYTHON:3.11"
```

#### GCP (Cloud Run)
```bash
gcloud run deploy contract-api --source .
```

---

## 🔒 Security Considerations

### Current (Demo)
- ⚠️ Hardcoded API key
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ Local file storage

### Production Recommendations
- ✅ Use environment variables for secrets
- ✅ Implement OAuth2/JWT authentication
- ✅ Add rate limiting (e.g., SlowAPI)
- ✅ Use cloud storage (S3, Azure Blob)
- ✅ Enable HTTPS only
- ✅ Add input validation
- ✅ Implement audit logging
- ✅ Use secrets manager (AWS Secrets Manager, Azure Key Vault)
- ✅ Add CORS middleware
- ✅ Implement virus scanning for uploads

---

## 📈 Performance Optimization

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_document_metadata(document_id: str):
    # Cached metadata retrieval
    pass
```

### Async Operations
All endpoints use `async def` for better concurrency.

### Vector Database Optimization
- Use persistent Chroma database
- Consider Pinecone or Weaviate for scale
- Implement connection pooling

### Load Testing
```bash
# Install Apache Bench
ab -n 1000 -c 10 http://localhost:8000/healthz
```

---

## 📞 Support & Troubleshooting

### Common Issues

#### Import Error: ModelProfileRegistry
```powershell
pip install --upgrade langchain langchain-openai langchain-community
```

#### Vector Database Not Found
```powershell
# Ensure you've ingested at least one document first
curl.exe -X POST http://localhost:8000/ingest -F "files=@contract.pdf"
```

#### OpenAI Rate Limit
- Upgrade OpenAI plan
- Implement request queuing
- Add retry logic with exponential backoff

#### Slow Response Times
- Reduce `k` parameter (fewer chunks)
- Use faster model (gpt-3.5-turbo)
- Add caching layer
- Scale horizontally

---

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **LangChain Docs**: https://python.langchain.com/
- **OpenAI API**: https://platform.openai.com/docs
- **Chroma DB**: https://www.trychroma.com/
- **Pydantic**: https://docs.pydantic.dev/

---

## 🎉 Conclusion

This Contract Analysis API provides a complete solution for:
- ✅ Automated contract ingestion
- ✅ AI-powered field extraction
- ✅ Intelligent Q&A with citations
- ✅ Real-time streaming responses
- ✅ Risk detection and auditing
- ✅ Production-ready monitoring

**Ready to analyze contracts at scale!** 🚀

---

**Version:** 1.0.0  
**Last Updated:** November 26, 2024  
**Author:** Contract Analysis Team  
**License:** MIT

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.schema import HumanMessage, SystemMessage
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, AsyncIterator
import asyncio

app = FastAPI(
    title="Contract Analysis API",
    description="API for contract ingestion, field extraction, and RAG-based Q&A",
    version="1.0.0"
)


OPENAI_API_KEY = "put you own key here"

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Directories
CHROMA_DIR = "./chroma_store"
UPLOAD_DIR = "./uploaded_contracts"
METADATA_DIR = "./contract_metadata"

# Create directories if they don't exist
Path(UPLOAD_DIR).mkdir(exist_ok=True)
Path(METADATA_DIR).mkdir(exist_ok=True)
Path(CHROMA_DIR).mkdir(exist_ok=True)

# In-memory document registry (in production, use a database)
document_registry: Dict[str, dict] = {}

# Metrics tracking
metrics = {
    "total_ingestions": 0,
    "total_extractions": 0,
    "total_questions": 0,
    "total_audits": 0,
    "total_streams": 0
}

# Server start time for uptime
import time
SERVER_START_TIME = time.time()


# -----------------------------
# PYDANTIC MODELS
# -----------------------------

class Signatory(BaseModel):
    name: str
    title: Optional[str] = None


class LiabilityCap(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None


class ContractFields(BaseModel):
    parties: List[str] = []
    effective_date: Optional[str] = None
    term: Optional[str] = None
    governing_law: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    auto_renewal: Optional[str] = None
    confidentiality: Optional[str] = None
    indemnity: Optional[str] = None
    liability_cap: Optional[LiabilityCap] = None
    signatories: List[Signatory] = []


class IngestResponse(BaseModel):
    document_ids: List[str]
    message: str
    total_chunks: int


class ExtractRequest(BaseModel):
    document_id: str


class ExtractResponse(BaseModel):
    document_id: str
    fields: ContractFields


class AskRequest(BaseModel):
    question: str
    document_ids: Optional[List[str]] = None
    k: int = Field(default=3, ge=1, le=10)


class Citation(BaseModel):
    document_id: str
    page: Optional[int] = None
    content: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]


class RiskFinding(BaseModel):
    risk_type: str
    severity: str  # "high", "medium", "low"
    description: str
    evidence: str
    recommendation: Optional[str] = None


class AuditRequest(BaseModel):
    document_id: str


class AuditResponse(BaseModel):
    document_id: str
    total_risks: int
    findings: List[RiskFinding]
    audit_date: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float


class MetricsResponse(BaseModel):
    total_documents: int
    total_ingestions: int
    total_extractions: int
    total_questions: int
    total_audits: int
    # total_streams: int


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def save_document_metadata(document_id: str, metadata: dict):
    """Save document metadata to JSON file"""
    metadata_path = Path(METADATA_DIR) / f"{document_id}.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def load_document_metadata(document_id: str) -> dict:
    """Load document metadata from JSON file"""
    metadata_path = Path(METADATA_DIR) / f"{document_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    with open(metadata_path, 'r') as f:
        return json.load(f)


def load_pdf(file_path):
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    return pages



def chunk_documents(documents, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)



def create_vector_db(chunks, document_id: str):
    """Create vector DB with document_id in metadata"""
    embedding = OpenAIEmbeddings()
    
    # Add document_id to each chunk's metadata
    for chunk in chunks:
        chunk.metadata["document_id"] = document_id
    
    vectordb = Chroma.from_documents(
        chunks,
        embedding,
        persist_directory=CHROMA_DIR
    )
    vectordb.persist()
    return vectordb



def load_vector_db():
    embedding = OpenAIEmbeddings()
    vectordb = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding
    )
    return vectordb



def ask_question(query, vectordb, k=3, document_ids: Optional[List[str]] = None):
    """Ask question with optional document_id filtering"""
    # Search for similar documents
    if document_ids:
        # Filter by document_ids
        docs = []
        all_docs = vectordb.similarity_search(query, k=k*5)  # Get more to filter
        for doc in all_docs:
            if doc.metadata.get("document_id") in document_ids:
                docs.append(doc)
                if len(docs) >= k:
                    break
    else:
        docs = vectordb.similarity_search(query, k=k)
    
    if not docs:
        return "No relevant information found in the specified documents.", []
    
    context = "\n\n".join([d.page_content for d in docs])

    llm = ChatOpenAI(model="gpt-4o-mini")

    prompt = [
        SystemMessage(content="You are a legal contract analysis assistant. Use ONLY the provided context to answer questions. Be precise and cite specific clauses when possible."),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
    ]

    answer = llm(prompt)
    return answer.content, docs



def extract_contract_fields(full_text) -> ContractFields:
    """Extract structured contract fields using LLM"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    system = """
    Extract structured contract fields from the provided text and return a valid JSON object with these exact keys:
    - parties: array of party names
    - effective_date: date as string
    - term: contract term/duration as string
    - governing_law: jurisdiction/law as string
    - payment_terms: payment details as string
    - termination: termination conditions as string
    - auto_renewal: auto-renewal clause as string
    - confidentiality: confidentiality terms as string
    - indemnity: indemnity clause as string
    - liability_cap: object with "amount" (number) and "currency" (string)
    - signatories: array of objects with "name" and "title"
    
    If a field is not found, use null for strings/objects or empty array for arrays.
    Return ONLY valid JSON, no additional text.
    """

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Contract text:\n\n{full_text[:8000]}")  # Limit text to avoid token limits
    ]

    resp = llm(messages)
    
    try:
        # Parse JSON response
        fields_dict = json.loads(resp.content)
        return ContractFields(**fields_dict)
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        return ContractFields()


def audit_contract_risks(full_text: str) -> List[RiskFinding]:
    """
    Detect risky clauses in contract using LLM analysis.
    Checks for:
    - Auto-renewal with <30 days notice
    - Unlimited liability
    - Broad indemnity clauses
    - Unfavorable termination terms
    - One-sided confidentiality
    - Unreasonable payment terms
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    system = """
    You are a contract risk auditor. Analyze the contract text and identify risky clauses.
    
    Focus on these risk categories:
    1. AUTO_RENEWAL_SHORT_NOTICE: Auto-renewal with less than 30 days notice period
    2. UNLIMITED_LIABILITY: No cap on liability or unreasonably high liability
    3. BROAD_INDEMNITY: Overly broad indemnification obligations
    4. UNFAVORABLE_TERMINATION: Difficult or one-sided termination conditions
    5. ONE_SIDED_CONFIDENTIALITY: Confidentiality only binding on one party
    6. UNREASONABLE_PAYMENT: Unfavorable payment terms or penalties
    7. UNILATERAL_CHANGES: Right to change terms without consent
    8. JURISDICTION_ISSUES: Unfavorable jurisdiction or governing law
    
    For each risk found, return a JSON array with objects containing:
    - risk_type: one of the categories above
    - severity: "high", "medium", or "low"
    - description: brief explanation of the risk
    - evidence: exact quote from contract (max 300 chars)
    - recommendation: suggested mitigation
    
    Return ONLY a valid JSON array, no additional text. If no risks found, return empty array [].
    """
    
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Analyze this contract for risks:\n\n{full_text[:10000]}")
    ]
    
    resp = llm(messages)
    
    try:
        # Parse JSON response
        findings_list = json.loads(resp.content)
        return [RiskFinding(**finding) for finding in findings_list]
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing audit response: {e}")
        return []


async def stream_answer(query: str, vectordb, k: int = 3, document_ids: Optional[List[str]] = None) -> AsyncIterator[str]:
    """
    Stream answer tokens in real-time using SSE.
    Yields tokens as they are generated by the LLM.
    """
    try:
        # Search for similar documents
        if document_ids:
            docs = []
            all_docs = vectordb.similarity_search(query, k=k*5)
            for doc in all_docs:
                if doc.metadata.get("document_id") in document_ids:
                    docs.append(doc)
                    if len(docs) >= k:
                        break
        else:
            docs = vectordb.similarity_search(query, k=k)
        
        if not docs:
            yield "data: " + json.dumps({"type": "error", "content": "No relevant information found"}) + "\n\n"
            return
        
        # Send citations first
        citations_data = []
        for doc in docs:
            citations_data.append({
                "document_id": doc.metadata.get("document_id", "unknown"),
                "page": doc.metadata.get("page"),
                "content": doc.page_content[:200]
            })
        
        yield "data: " + json.dumps({"type": "citations", "content": citations_data}) + "\n\n"
        
        # Build context
        context = "\n\n".join([d.page_content for d in docs])
        
        # Stream LLM response
        llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
        
        prompt = [
            SystemMessage(content="You are a legal contract analysis assistant. Use ONLY the provided context to answer questions. Be precise and cite specific clauses when possible."),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
        ]
        
        # Stream tokens
        for chunk in llm.stream(prompt):
            if chunk.content:
                yield "data: " + json.dumps({"type": "token", "content": chunk.content}) + "\n\n"
                await asyncio.sleep(0.01)  # Small delay for better streaming effect
        
        # Send completion signal
        yield "data: " + json.dumps({"type": "done", "content": ""}) + "\n\n"
        
    except Exception as e:
        yield "data: " + json.dumps({"type": "error", "content": str(e)}) + "\n\n"



# -----------------------------
# API ENDPOINTS
# -----------------------------

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Contract Analysis API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "ingest": "POST /ingest - Upload PDF contracts",
            "extract": "POST /extract - Extract contract fields",
            "ask": "POST /ask - Ask questions about contracts",
            "audit": "POST /audit - Detect risky clauses",
            "documents": "GET /documents - List all documents",
            "stream": "GET /ask/stream - Stream answers in real-time (SSE)",
            "healthz": "GET /healthz - Health check",
            "metrics": "GET /metrics - API metrics"
        }
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_contracts(files: List[UploadFile] = File(...)):
    """
    API 1: INGEST
    Upload 1 to N PDF contracts, process them, and store in vector database.
    Returns document_ids for later extraction and querying.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    document_ids = []
    total_chunks = 0
    
    try:
        for file in files:
            # Validate file type
            if not file.filename.endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a PDF"
                )
            
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Save uploaded file
            file_path = Path(UPLOAD_DIR) / f"{document_id}_{file.filename}"
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Load and process PDF
            print(f"Loading PDF: {file.filename}")
            docs = load_pdf(str(file_path))
            
            # Chunk documents
            print(f"Chunking {file.filename}...")
            chunks = chunk_documents(docs)
            total_chunks += len(chunks)
            
            # Create/update vector DB with document_id in metadata
            print(f"Storing in vector DB...")
            vectordb = create_vector_db(chunks, document_id)
            
            # Extract full text for metadata
            full_text = "\n".join([d.page_content for d in docs])
            
            # Save document metadata
            metadata = {
                "document_id": document_id,
                "filename": file.filename,
                "upload_date": datetime.now().isoformat(),
                "num_pages": len(docs),
                "num_chunks": len(chunks),
                "file_path": str(file_path),
                "full_text_preview": full_text[:500]  # First 500 chars
            }
            save_document_metadata(document_id, metadata)
            document_registry[document_id] = metadata
            
            document_ids.append(document_id)
            print(f"✓ Processed {file.filename} -> {document_id}")
        
        # Update metrics
        metrics["total_ingestions"] += len(files)
        
        return IngestResponse(
            document_ids=document_ids,
            message=f"Successfully ingested {len(files)} document(s)",
            total_chunks=total_chunks
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@app.post("/extract", response_model=ExtractResponse)
async def extract_fields(request: ExtractRequest):
    """
    API 2: EXTRACT
    Extract structured contract fields from a previously ingested document.
    Returns JSON with parties, dates, terms, and other contract details.
    """
    document_id = request.document_id
    
    try:
        # Load document metadata
        metadata = load_document_metadata(document_id)
        
        # Load the PDF file
        file_path = metadata.get("file_path")
        if not file_path or not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"PDF file for document {document_id} not found"
            )
        
        # Load PDF and extract full text
        print(f"Extracting fields from document {document_id}...")
        docs = load_pdf(file_path)
        full_text = "\n".join([d.page_content for d in docs])
        
        # Extract structured fields using LLM
        fields = extract_contract_fields(full_text)
        
        # Save extracted fields to metadata
        metadata["extracted_fields"] = fields.dict()
        metadata["extraction_date"] = datetime.now().isoformat()
        save_document_metadata(document_id, metadata)
        
        # Update metrics
        metrics["total_extractions"] += 1
        
        return ExtractResponse(
            document_id=document_id,
            fields=fields
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting fields: {str(e)}"
        )


@app.post("/ask", response_model=AskResponse)
async def ask_question_api(request: AskRequest):
    """
    API 3: ASK (RAG)
    Ask questions about uploaded contracts using RAG.
    Returns answer grounded in documents with citations (document_id, page, content).
    """
    try:
        # Load vector database
        vectordb = load_vector_db()
        
        # Validate document_ids if provided
        if request.document_ids:
            for doc_id in request.document_ids:
                metadata_path = Path(METADATA_DIR) / f"{doc_id}.json"
                if not metadata_path.exists():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document {doc_id} not found"
                    )
        
        # Ask question with optional document filtering
        answer, docs = ask_question(
            request.question,
            vectordb,
            k=request.k,
            document_ids=request.document_ids
        )
        
        # Build citations
        citations = []
        for doc in docs:
            citation = Citation(
                document_id=doc.metadata.get("document_id", "unknown"),
                page=doc.metadata.get("page", None),
                content=doc.page_content[:200]  # First 200 chars
            )
            citations.append(citation)
        
        # Update metrics
        metrics["total_questions"] += 1
        
        return AskResponse(
            question=request.question,
            answer=answer,
            citations=citations
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error answering question: {str(e)}"
        )


@app.get("/documents")
async def list_documents():
    """List all ingested documents"""
    documents = []
    for doc_id in Path(METADATA_DIR).glob("*.json"):
        with open(doc_id, 'r') as f:
            metadata = json.load(f)
            documents.append({
                "document_id": metadata["document_id"],
                "filename": metadata["filename"],
                "upload_date": metadata["upload_date"],
                "num_pages": metadata["num_pages"],
                "num_chunks": metadata["num_chunks"]
            })
    
    return {"documents": documents, "total": len(documents)}


# @app.get("/ask/stream")
# async def ask_question_stream(
#     question: str = Query(..., description="The question to ask about the contracts"),
#     document_ids: Optional[str] = Query(None, description="Comma-separated document IDs to filter (optional)"),
#     k: int = Query(default=3, ge=1, le=10, description="Number of relevant chunks to retrieve")
# ):
#     """
#     API 7: STREAM (SSE)
#     Stream answer tokens in real-time using Server-Sent Events.
    
#     Query parameters:
#     - question: The question to ask
#     - document_ids: Optional comma-separated list of document IDs to search within
#     - k: Number of relevant document chunks to retrieve (1-10)
    
#     Response format (SSE):
#     - type: "citations" - Initial citations sent first
#     - type: "token" - Individual answer tokens as they are generated
#     - type: "done" - Completion signal
#     - type: "error" - Error message if something goes wrong
    
#     Example usage:
#     ```javascript
#     const eventSource = new EventSource('/ask/stream?question=What is the governing law?&k=3');
#     eventSource.onmessage = (event) => {
#         const data = JSON.parse(event.data);
#         if (data.type === 'token') {
#             console.log(data.content);
#         }
#     };
#     ```
#     """
#     try:
#         # Load vector database
#         vectordb = load_vector_db()
        
#         # Parse document_ids if provided
#         doc_ids_list = None
#         if document_ids:
#             doc_ids_list = [did.strip() for did in document_ids.split(",")]
#             # Validate document_ids
#             for doc_id in doc_ids_list:
#                 metadata_path = Path(METADATA_DIR) / f"{doc_id}.json"
#                 if not metadata_path.exists():
#                     raise HTTPException(
#                         status_code=404,
#                         detail=f"Document {doc_id} not found"
#                     )
        
#         # Update metrics
#         metrics["total_streams"] += 1
        
#         # Return streaming response
#         return StreamingResponse(
#             stream_answer(question, vectordb, k=k, document_ids=doc_ids_list),
#             media_type="text/event-stream",
#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "X-Accel-Buffering": "no"  # Disable nginx buffering
#             }
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error streaming answer: {str(e)}"
#         )


@app.post("/audit", response_model=AuditResponse)
async def audit_contract(request: AuditRequest):
    """
    API 4: AUDIT
    Detect risky clauses in a contract.
    Identifies risks like:
    - Auto-renewal with <30 days notice
    - Unlimited liability
    - Broad indemnity clauses
    - Unfavorable termination terms
    - One-sided confidentiality
    - Unreasonable payment terms
    
    Returns list of findings with severity and evidence.
    """
    document_id = request.document_id
    
    try:
        # Load document metadata
        metadata = load_document_metadata(document_id)
        
        # Load the PDF file
        file_path = metadata.get("file_path")
        if not file_path or not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"PDF file for document {document_id} not found"
            )
        
        # Load PDF and extract full text
        print(f"Auditing document {document_id} for risks...")
        docs = load_pdf(file_path)
        full_text = "\n".join([d.page_content for d in docs])
        
        # Perform risk audit using LLM
        findings = audit_contract_risks(full_text)
        
        # Save audit results to metadata
        audit_results = {
            "audit_date": datetime.now().isoformat(),
            "total_risks": len(findings),
            "findings": [f.dict() for f in findings]
        }
        metadata["audit_results"] = audit_results
        save_document_metadata(document_id, metadata)
        
        # Update metrics
        metrics["total_audits"] += 1
        
        return AuditResponse(
            document_id=document_id,
            total_risks=len(findings),
            findings=findings,
            audit_date=audit_results["audit_date"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error auditing contract: {str(e)}"
        )


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    API 5: HEALTH CHECK
    Returns server health status and uptime.
    """
    uptime = time.time() - SERVER_START_TIME
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=round(uptime, 2)
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    API 6: METRICS
    Returns basic API usage metrics and counters.
    """
    total_documents = len(list(Path(METADATA_DIR).glob("*.json")))
    
    return MetricsResponse(
        total_documents=total_documents,
        total_ingestions=metrics["total_ingestions"],
        total_extractions=metrics["total_extractions"],
        total_questions=metrics["total_questions"],
        total_audits=metrics["total_audits"],
        
    )


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("CONTRACT ANALYSIS API - COMPLETE SYSTEM")
    print("=" * 70)
    print("Starting server...")
    print("\n📋 Core Endpoints:")
    print("  • POST /ingest       - Upload & process PDFs")
    print("  • POST /extract      - Extract contract fields")
    print("  • POST /ask          - Ask questions (RAG)")
    print("  • GET  /ask/stream   - Stream answers in real-time (SSE)")
    print("  • POST /audit        - Detect risky clauses")
    print("\n📊 Admin Endpoints:")
    print("  • GET  /documents    - List all documents")
    print("  • GET  /healthz      - Health check")
    print("  • GET  /metrics      - API usage metrics")
    print("\n📚 Documentation:")
    print("  • Swagger UI: http://localhost:8000/docs")
    print("  • ReDoc:      http://localhost:8000/redoc")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8000)

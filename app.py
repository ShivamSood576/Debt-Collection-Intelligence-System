import os
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.schema import HumanMessage, SystemMessage


OPENAI_API_KEY = "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"

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# local vector DB folder
CHROMA_DIR = "./chroma_store"



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



def create_vector_db(chunks):
    embedding = OpenAIEmbeddings()
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



def ask_question(query, vectordb, k=3):
    docs = vectordb.similarity_search(query, k=k)
    context = "\n\n".join([d.page_content for d in docs])

    llm = ChatOpenAI(model="gpt-4.1")

    prompt = [
        SystemMessage(content="You are a legal contract analysis assistant. Use ONLY the provided context."),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
    ]

    answer = llm(prompt)
    return answer.content, docs



def extract_contract_fields(full_text):
    llm = ChatOpenAI(model="gpt-4.1")

    system = """
    Extract structured contract fields in JSON with keys:
    parties, effective_date, term, governing_law, payment_terms,
    termination, auto_renewal, confidentiality, indemnity,
    liability_cap, signatories.
    If missing, return null.
    """

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=full_text)
    ]

    resp = llm(messages)
    return resp.content



def ingest_pdf(file_path):
    print(f"Loading PDF: {file_path}")
    docs = load_pdf(file_path)

    print("Chunking...")
    chunks = chunk_documents(docs)

    print("Building vector DB...")
    vectordb = create_vector_db(chunks)

    print("Extracting full text for structured fields...")
    full_text = "\n".join([d.page_content for d in docs])

    fields_json = extract_contract_fields(full_text)

    return {
        "chunks": len(chunks),
        "fields": fields_json
    }


# -----------------------------
# 8. SIMPLE TEST
# -----------------------------
if __name__ == "__main__":
    # Path to your PDF
    pdf_path = r"D:\JOB project\Master-Services-Agreement.pdf"

    # Ingest
    result = ingest_pdf(pdf_path)
    print("\n------------- STRUCTURED FIELDS -------------")
    print(result["fields"])

    # Ask a question
    vectordb = load_vector_db()
    question = "What is the governing law?"
    answer, citations = ask_question(question, vectordb)

    print("\n------------- ANSWER -------------")
    print(answer)

    print("\n------------- CITATIONS (Chunks) -------------")
    for c in citations:
        print(c.metadata)

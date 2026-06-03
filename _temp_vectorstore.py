import chromadb
from app.config import CHROMA_DIR
from typing import List

# 🔧 优化: ChromaDB客户端单例
_chroma_client: chromadb.PersistentClient = None

def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create singleton ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def get_or_create_collection(name: str = "knowledge_base"):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_documents(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split long document into overlapping chunks for better retrieval.
    
    Args:
        text: Full document text
        chunk_size: Max characters per chunk
        overlap: Characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    # 先按段落分割
    paragraphs = text.split("\n\n")
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 处理超长段落
            if len(para) > chunk_size:
                # 按字符切分
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size].strip())
                current_chunk = ""
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return [c for c in chunks if c]  # 过滤空chunk


def add_documents(collection_name: str, documents: list, metadatas: list = None, ids: list = None,
                  chunk_size: int = 500, overlap: int = 50):
    """Add documents to vector store with auto-chunking.
    
    Args:
        collection_name: Name of the collection
        documents: List of document texts
        metadatas: Optional metadata for each document
        ids: Optional IDs (auto-generated if not provided)
        chunk_size: Max characters per chunk
        overlap: Overlap between chunks
    """
    collection = get_or_create_collection(collection_name)
    
    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    for i, doc in enumerate(documents):
        chunks = chunk_documents(doc, chunk_size, overlap)
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            meta = (metadatas[i] if metadatas else {}).copy()
            meta["chunk_index"] = j
            meta["total_chunks"] = len(chunks)
            all_metadatas.append(meta)
            all_ids.append(f"doc_{i}_chunk_{j}_{hash(chunk) % 100000}")
    
    if all_chunks:
        collection.add(
            documents=all_chunks,
            metadatas=all_metadatas,
            ids=all_ids,
        )
    
    return f"Added {len(all_chunks)} chunks from {len(documents)} documents to '{collection_name}'"


def query_collection(collection_name: str, query: str, n_results: int = 5) -> list:
    """Query the vector store and return relevant documents."""
    collection = get_or_create_collection(collection_name)
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    
    return [
        {
            "content": doc,
            "distance": dist,
            "metadata": meta,
        }
        for doc, dist, meta in zip(documents, distances, metadatas)
    ]


def list_collections() -> list:
    client = get_chroma_client()
    return [c.name for c in client.list_collections()]


def delete_collection(name: str):
    client = get_chroma_client()
    try:
        client.delete_collection(name)
        return f"Collection '{name}' deleted"
    except Exception as e:
        return f"Error: {e}"

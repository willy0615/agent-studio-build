from app.rag.vectorstore import query_collection
from typing import List, Dict


def rag_retrieve(query: str, collection_name: str = "knowledge_base", n_results: int = 5) -> str:
    """Retrieve relevant context from RAG knowledge base.
    
    Returns:
        Formatted context string for LLM, or empty string if no results.
    """
    try:
        results = query_collection(collection_name, query, n_results)
        if not results:
            return ""
        
        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            filename = meta.get("filename", "unknown")
            content = r["content"]
            distance = r.get("distance", 0)
            
            # 过滤距离太远的结果
            if distance > 1.5:
                continue
            
            context_parts.append(f"[{i}] (from {filename}, relevance: {1-distance:.2f})\n{content}")
        
        return "\n\n---\n\n".join(context_parts) if context_parts else ""
    
    except Exception as e:
        return f"[RAG Error: {e}]"

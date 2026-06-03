"""知识图谱可视化 - RAG知识库图形化展示"""
from typing import Dict, List, Any, Tuple
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self, chroma_db_path: str = None):
        """
        Args:
            chroma_db_path: ChromaDB数据库路径
        """
        self.db_path = Path(chroma_db_path or "E:/AgentProject/data/chroma_db")
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            collection_name: 集合名称
        
        Returns:
            统计信息
        """
        try:
            import chromadb
            
            client = chromadb.PersistentClient(path=str(self.db_path))
            collection = client.get_collection(collection_name)
            
            count = collection.count()
            
            return {
                "success": True,
                "name": collection_name,
                "document_count": count,
                "metadata": collection.metadata,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def get_document_nodes(self, collection_name: str, limit: int = 100) -> List[Dict]:
        """
        获取文档节点
        
        Args:
            collection_name: 集合名称
            limit: 最大节点数
        
        Returns:
            节点列表
        """
        try:
            import chromadb
            
            client = chromadb.PersistentClient(path=str(self.db_path))
            collection = client.get_collection(collection_name)
            
            # 获取所有文档
            result = collection.get(limit=limit, include=["documents", "metadatas"])
            
            nodes = []
            for i, (doc, metadata) in enumerate(zip(result["documents"], result["metadatas"])):
                # 提取关键词作为标签
                label = self._extract_label(doc, metadata)
                
                nodes.append({
                    "id": f"node_{i}",
                    "label": label,
                    "title": doc[:100] + "..." if len(doc) > 100 else doc,
                    "metadata": metadata,
                    "size": min(30, max(10, len(doc) // 50)),  # 根据文档长度设置大小
                })
            
            return nodes
        except Exception as e:
            logger.error(f"Failed to get document nodes: {e}")
            return []
    
    def get_document_edges(self, collection_name: str, nodes: List[Dict]) -> List[Dict]:
        """
        获取文档关联边（基于相似度）
        
        Args:
            collection_name: 集合名称
            nodes: 节点列表
        
        Returns:
            边列表
        """
        try:
            import chromadb
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np
                HAS_SKLEARN = True
            except ImportError:
                HAS_SKLEARN = False
            
            if len(nodes) < 2:
                return []
            
            if not HAS_SKLEARN:
                logger.warning("sklearn not installed, skipping edge generation")
                return []
            
            client = chromadb.PersistentClient(path=str(self.db_path))
            collection = client.get_collection(collection_name)
            
            # 获取文档内容
            result = collection.get(
                ids=[n["id"] for n in nodes],
                include=["documents"]
            )
            
            documents = result["documents"]
            
            # 计算TF-IDF相似度
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(documents)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            edges = []
            threshold = 0.3  # 相似度阈值
            
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    similarity = similarity_matrix[i][j]
                    
                    if similarity >= threshold:
                        edges.append({
                            "source": nodes[i]["id"],
                            "target": nodes[j]["id"],
                            "weight": float(similarity),
                            "title": f"相似度: {similarity:.2f}",
                        })
            
            return edges
        except Exception as e:
            logger.error(f"Failed to get document edges: {e}")
            return []
    
    def generate_pyvis_graph(
        self,
        collection_name: str,
        output_path: str = None,
        height: str = "600px",
        width: str = "100%",
    ) -> str:
        """
        生成Pyvis交互式知识图谱
        
        Args:
            collection_name: 集合名称
            output_path: 输出文件路径
            height: 图高度
            width: 图宽度
        
        Returns:
            HTML文件路径
        """
        try:
            from pyvis.network import Network
            
            # 获取节点和边
            nodes = self.get_document_nodes(collection_name, limit=50)
            edges = self.get_document_edges(collection_name, nodes)
            
            # 创建网络图
            net = Network(
                height=height,
                width=width,
                bgcolor="#222222",
                font_color="white",
                select_menu=True,
                filter_menu=True,
            )
            
            # 添加节点
            for node in nodes:
                net.add_node(
                    node["id"],
                    label=node["label"],
                    title=node["title"],
                    size=node["size"],
                    color=self._get_node_color(node),
                )
            
            # 添加边
            for edge in edges:
                net.add_edge(
                    edge["source"],
                    edge["target"],
                    weight=edge["weight"],
                    title=edge["title"],
                    color="#888888",
                )
            
            # 设置布局
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -3000,
                        "centralGravity": 0.3,
                        "springLength": 100
                    }
                },
                "nodes": {
                    "font": {
                        "size": 12,
                        "face": "Arial"
                    }
                }
            }
            """)
            
            # 保存
            output_path = output_path or f"E:/AgentProject/data/knowledge_graph_{collection_name}.html"
            net.save_graph(output_path)
            
            logger.info(f"Generated knowledge graph: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate pyvis graph: {e}")
            return None
    
    def generate_graphviz_dot(self, collection_name: str) -> str:
        """
        生成Graphviz DOT格式（用于Streamlit显示）
        
        Args:
            collection_name: 集合名称
        
        Returns:
            DOT格式字符串
        """
        try:
            nodes = self.get_document_nodes(collection_name, limit=30)
            edges = self.get_document_edges(collection_name, nodes)
            
            dot_lines = [
                "digraph KnowledgeGraph {",
                "    rankdir=LR;",
                "    node [shape=box, style=filled, fillcolor=lightblue];",
                "    edge [color=gray];",
            ]
            
            # 添加节点
            for node in nodes:
                label = node["label"].replace('"', "'")
                dot_lines.append(f'    "{node["id"]}" [label="{label}"];')
            
            # 添加边
            for edge in edges:
                dot_lines.append(f'    "{edge["source"]}" -> "{edge["target"]}";')
            
            dot_lines.append("}")
            
            return "\n".join(dot_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate graphviz dot: {e}")
            return "digraph {}"
    
    def generate_mermaid_diagram(self, collection_name: str) -> str:
        """
        生成Mermaid格式图表（用于Markdown）
        
        Args:
            collection_name: 集合名称
        
        Returns:
            Mermaid格式字符串
        """
        try:
            nodes = self.get_document_nodes(collection_name, limit=20)
            edges = self.get_document_edges(collection_name, nodes)
            
            mermaid_lines = ["graph TD"]
            
            # 添加节点
            for node in nodes:
                label = node["label"].replace('"', "'")[:20]
                mermaid_lines.append(f'    {node["id"]}["{label}"]')
            
            # 添加边
            for edge in edges[:50]:  # 限制边数量
                mermaid_lines.append(f'    {edge["source"]} --> {edge["target"]}')
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate mermaid diagram: {e}")
            return "graph TD\n    A[Error]"
    
    def get_topic_clusters(self, collection_name: str, n_clusters: int = 5) -> List[Dict]:
        """
        获取主题聚类
        
        Args:
            collection_name: 集合名称
            n_clusters: 聚类数量
        
        Returns:
            聚类结果
        """
        try:
            import chromadb
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.cluster import KMeans
                HAS_SKLEARN = True
            except ImportError:
                logger.warning("sklearn not installed, cannot compute topic clusters")
                return []
            
            client = chromadb.PersistentClient(path=str(self.db_path))
            collection = client.get_collection(collection_name)
            
            # 获取文档
            result = collection.get(include=["documents"])
            documents = result["documents"]
            
            if len(documents) < n_clusters:
                n_clusters = max(1, len(documents))
            
            # TF-IDF向量化
            vectorizer = TfidfVectorizer(max_features=100)
            X = vectorizer.fit_transform(documents)
            
            # K-Means聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(X)
            
            # 整理结果
            clusters = []
            for i in range(n_clusters):
                cluster_docs = [documents[j] for j in range(len(documents)) if labels[j] == i]
                
                # 提取主题词
                feature_names = vectorizer.get_feature_names_out()
                cluster_center = kmeans.cluster_centers_[i]
                top_indices = cluster_center.argsort()[-5:][::-1]
                top_words = [feature_names[idx] for idx in top_indices]
                
                clusters.append({
                    "cluster_id": i,
                    "document_count": len(cluster_docs),
                    "top_keywords": top_words,
                    "sample_documents": cluster_docs[:3],
                })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to get topic clusters: {e}")
            return []
    
    @staticmethod
    def _extract_label(doc: str, metadata: Dict) -> str:
        """提取节点标签"""
        # 优先使用文件名
        if metadata and "filename" in metadata:
            return Path(metadata["filename"]).stem
        
        # 提取第一行或前30个字符
        first_line = doc.split("\n")[0].strip()
        if first_line:
            return first_line[:30]
        
        return doc[:30] + "..."
    
    @staticmethod
    def _get_node_color(node: Dict) -> str:
        """根据节点类型获取颜色"""
        metadata = node.get("metadata", {})
        
        filename = metadata.get("filename", "")
        
        if filename.endswith((".py", ".js", ".ts")):
            return "#4CAF50"  # 绿色 - 代码
        elif filename.endswith((".md", ".txt")):
            return "#2196F3"  # 蓝色 - 文本
        elif filename.endswith(".pdf"):
            return "#FF9800"  # 橙色 - PDF
        elif filename.endswith((".xlsx", ".csv")):
            return "#9C27B0"  # 紫色 - 数据
        else:
            return "#607D8B"  # 灰色 - 其他


# 全局实例
_visualizer = None


def get_visualizer() -> KnowledgeGraphVisualizer:
    """获取全局可视化器实例"""
    global _visualizer
    if _visualizer is None:
        _visualizer = KnowledgeGraphVisualizer()
    return _visualizer

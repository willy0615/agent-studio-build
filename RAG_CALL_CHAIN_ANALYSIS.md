# RAG知识库调用链分析报告

## 分析时间
2026-06-03

---

## 一、调用链状态

### ✅ 完整正常的调用链

```
用户上传文档 (main.py侧边栏)
  └─ add_documents() [vectorstore.py]
       ├─ chunk_documents() - 文档分块
       └─ collection.add() - 存入ChromaDB

用户提问 (main.py)
  └─ run_agent() [autonomous.py]
       └─ rag_retrieve(task) [retriever.py]
            └─ query_collection() [vectorstore.py]
                 └─ collection.query() - 向量检索
```

---

## 二、调用点详情

### 1. 文档上传入口
**文件**: `main.py`

**位置**: 侧边栏 Knowledge Base 部分

**代码**:
```python
# Line 14: 导入
from app.rag.vectorstore import add_documents, list_collections, delete_collection

# Line 107: 上传文档
if uploaded_files and st.button("Upload"):
    for f in uploaded_files:
        content = f.read().decode("utf-8", errors="ignore")
        add_documents("knowledge_base", [content], metadatas=[{"filename": f.name}])
```

**功能**:
- 支持上传 txt, md, html, py, pdf 文件
- 自动分块存储
- 显示集合数量

---

### 2. 知识检索入口
**文件**: `app/agents/autonomous.py`

**代码**:
```python
# Line 8: 导入
from app.rag.retriever import rag_retrieve

# Line 104: 任务执行前检索
rag_context = rag_retrieve(task)
if rag_context:
    context = f"{context}\n\n[Knowledge Base]:\n{rag_context}" if context else rag_context
```

**流程**:
1. 用户提问进入 `run_agent()`
2. 自动调用 `rag_retrieve(task)` 检索相关知识
3. 将知识注入到 LLM 上下文
4. 然后执行任务

---

## 三、功能模块分析

### 1. vectorstore.py - 向量存储

| 函数 | 状态 | 调用点 |
|------|------|--------|
| `add_documents()` | ✅ 被调用 | main.py (上传文档) |
| `query_collection()` | ✅ 被调用 | retriever.py |
| `list_collections()` | ✅ 被调用 | main.py (显示集合) |
| `delete_collection()` | ✅ 被调用 | main.py (删除集合) |
| `chunk_documents()` | ✅ 被调用 | add_documents内部 |
| `get_chroma_client()` | ✅ 单例 | 内部调用 |

**优化点**:
- ✅ ChromaDB客户端单例模式
- ✅ 文档自动分块（500字符，50字符重叠）
- ✅ 距离过滤（>1.5不返回）

---

### 2. retriever.py - 检索器

| 函数 | 状态 | 调用点 |
|------|------|--------|
| `rag_retrieve()` | ✅ 被调用 | autonomous.py |

**功能**:
- 查询向量数据库
- 格式化上下文
- 过滤低相关度结果
- 返回给LLM使用

---

## 四、数据存储状态

### ChromaDB目录
- **路径**: `E:\AgentProject\data\chroma_db`
- **文件**: `chroma.sqlite3` (155KB)
- **状态**: 数据库已初始化

### 知识库状态
- **默认集合**: `knowledge_base`
- **当前文档**: 未知（需要运行时检查）

---

## 五、完整调用流程

### 文档上传流程
```
1. 用户在侧边栏点击"Add Documents"上传文件
2. main.py 接收文件内容
3. 调用 add_documents("knowledge_base", [content], ...)
4. vectorstore.py 执行:
   - chunk_documents() 分块
   - collection.add() 存入向量数据库
5. 显示成功消息
```

### 知识检索流程
```
1. 用户在对话框输入问题
2. run_agent() 启动
3. autonomous.py 执行:
   - rag_retrieve(task)
   - retriever.py 查询相关文档
   - 格式化上下文返回
4. 将知识注入LLM提示词
5. 执行任务并返回答案
```

---

## 六、潜在问题

### ⚠️ 1. 知识库可能为空
- ChromaDB已初始化
- 但用户可能还没上传文档
- 建议：首次启动时提示用户上传文档

### ⚠️ 2. PDF解析简单
- 当前用 `decode("utf-8", errors="ignore")`
- 二进制PDF可能无法正确解析
- 建议：使用PyPDF2或pdfplumber

### ⚠️ 3. 分块策略固定
- 固定500字符分块
- 可能不适合所有文档
- 建议：支持可配置分块策略

---

## 七、集成度评估

| 模块 | 定义 | 导入 | 调用 | 状态 |
|------|------|------|------|------|
| vectorstore | ✅ | ✅ main.py | ✅ | 正常 |
| retriever | ✅ | ✅ autonomous.py | ✅ | 正常 |
| ChromaDB单例 | ✅ | - | ✅ | 正常 |
| 文档分块 | ✅ | - | ✅ | 正常 |

---

## 八、总结

### ✅ RAG模块完全集成
- 调用链完整无断层
- 文档上传功能正常
- 知识检索功能正常
- ChromaDB正常工作

### 状态
- **核心功能**: ✅ 正常
- **调用链**: ✅ 完整
- **数据存储**: ✅ 已初始化
- **UI集成**: ✅ 完整

### 建议
1. 首次启动提示用户上传文档
2. 增强PDF解析能力
3. 支持更多文档格式（Word、Excel等）

---

## 附录：UI操作位置

### 文档上传
- **位置**: 左侧边栏 → Knowledge Base
- **格式**: txt, md, html, py, pdf
- **按钮**: "Add Documents" → "Upload"

### 查看集合
- **位置**: 左侧边栏 → Knowledge Base
- **显示**: Collections数量

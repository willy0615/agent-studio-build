# 数据分析插件

自动分析CSV、Excel数据文件，生成统计摘要和可视化。

## 功能

### 1. quick_stats - 快速统计
快速统计分析数据文件，生成概览信息。

**参数**:
- `file_path`: 数据文件路径（CSV或Excel）

**返回**:
- 行数、列数、内存占用
- 列信息（数据类型、缺失值）
- 数值列统计摘要

### 2. correlation_analysis - 相关性分析
计算数据列之间的相关性。

**参数**:
- `file_path`: 数据文件路径
- `method`: 相关性方法（pearson/kendall/spearman）

**返回**:
- 相关性矩阵
- 强相关性列表（>0.7）

### 3. data_quality_check - 数据质量检查
检查数据质量，发现潜在问题。

**参数**:
- `file_path`: 数据文件路径

**返回**:
- 缺失值报告
- 重复行统计
- 异常值检测
- 改进建议

## 使用

```python
from app.agents.plugins import get_plugin_manager

# 加载插件
pm = get_plugin_manager()
pm.load_plugin("data_analysis")

# 使用工具
result = pm.plugins["data_analysis"].tools[0]["function"]("data.csv")
print(result)
```

## 依赖

- pandas

## 示例

```
用户: 分析 sales.xlsx
Agent: [调用 quick_stats]
📊 数据概览
- 行数: 1000
- 列数: 5
- 内存: 156.25 KB

📋 列信息
- date: datetime64[ns] (缺失: 0)
- product: object (缺失: 5)
- quantity: int64 (缺失: 0)
- price: float64 (缺失: 0)
- total: float64 (缺失: 0)

📈 数值列统计
       quantity      price      total
count   1000.00    1000.00    1000.00
mean      15.30     125.50    1920.15
...
```

## 作者

AI Agent

## 版本历史

- 1.0.0 (2026-06-03): 初始版本

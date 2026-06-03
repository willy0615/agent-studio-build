"""数据分析工具 - Excel、CSV、统计分析、图表生成"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def analyze_data(
    file_path: str,
    analysis_type: str = "summary",
    query: str = None
) -> Dict[str, Any]:
    """Analyze data from CSV or Excel file.
    
    Args:
        file_path: Path to data file
        analysis_type: Type of analysis (summary, stats, query, visualize)
        query: Natural language query about the data
    
    Returns:
        {
            "success": bool,
            "result": str or dict,
            "error": str (if failed)
        }
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Load data
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        elif path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            return {"success": False, "error": f"Unsupported file type: {path.suffix}"}
        
        # Perform analysis
        if analysis_type == "summary":
            result = _generate_summary(df)
        elif analysis_type == "stats":
            result = _generate_stats(df)
        elif analysis_type == "query" and query:
            result = _query_data(df, query)
        else:
            result = _generate_summary(df)
        
        return {
            "success": True,
            "result": result,
            "shape": df.shape,
            "columns": list(df.columns),
        }
        
    except Exception as e:
        logger.error(f"Data analysis failed: {e}")
        return {"success": False, "error": str(e)}


def _generate_summary(df: pd.DataFrame) -> str:
    """Generate data summary."""
    parts = []
    
    parts.append(f"Data Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    parts.append("")
    parts.append("Columns:")
    for col in df.columns:
        dtype = df[col].dtype
        non_null = df[col].notna().sum()
        parts.append(f"  - {col} ({dtype}): {non_null}/{len(df)} non-null")
    
    parts.append("")
    parts.append("First 5 rows:")
    parts.append(df.head().to_string())
    
    # Numeric columns statistics
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        parts.append("")
        parts.append("Numeric Statistics:")
        parts.append(df[numeric_cols].describe().to_string())
    
    return "\n".join(parts)


def _generate_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate detailed statistics."""
    stats = {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
        "numeric_stats": {},
    }
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        stats["numeric_stats"] = df[numeric_cols].describe().to_dict()
    
    # Categorical columns unique values
    cat_cols = df.select_dtypes(include=['object']).columns
    if len(cat_cols) > 0:
        stats["categorical_stats"] = {
            col: {
                "unique": df[col].nunique(),
                "top_values": df[col].value_counts().head(5).to_dict()
            }
            for col in cat_cols
        }
    
    return stats


def _query_data(df: pd.DataFrame, query: str) -> str:
    """Query data using natural language (generate and execute pandas code)."""
    from app.llm_client import chat_completion
    
    # Get data schema
    schema = f"""DataFrame with columns:
{json.dumps(list(df.columns))}
Types: {json.dumps({col: str(dtype) for col, dtype in df.dtypes.items()})}
First few rows:
{df.head(3).to_dict()}
"""
    
    # Generate pandas code
    prompt = f"""Given this pandas DataFrame:
{schema}

Write a pandas code snippet to answer this query: "{query}"

Rules:
1. The DataFrame variable is named 'df'
2. Return only the code, no explanations
3. Use print() to output results
4. Keep it simple and safe

Code:"""
    
    response = chat_completion([{"role": "user", "content": prompt}])
    code = response.choices[0].message.content
    
    # Extract code from markdown if present
    import re
    code_match = re.search(r'```(?:python)?\n(.*?)```', code, re.DOTALL)
    if code_match:
        code = code_match.group(1)
    
    # Execute code safely
    try:
        local_vars = {"df": df, "pd": pd}
        output_buffer = []
        
        # Capture print output
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        exec(code, {"__builtins__": {}}, local_vars)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        return f"Query: {query}\n\nResult:\n{output}"
        
    except Exception as e:
        return f"Query execution failed: {e}\n\nGenerated code:\n{code}"


def create_chart(
    data: Dict[str, List],
    chart_type: str = "bar",
    title: str = None,
    output_path: str = None
) -> Dict[str, Any]:
    """Create a chart from data.
    
    Args:
        data: {"labels": [...], "values": [...]} or {"x": [...], "y": [...]}
        chart_type: bar, line, pie, scatter
        title: Chart title
        output_path: Path to save chart (default: temp file)
    
    Returns:
        {
            "success": bool,
            "path": str,
            "error": str (if failed)
        }
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        # Extract labels and values
        labels = data.get("labels") or data.get("x", [])
        values = data.get("values") or data.get("y", [])
        
        if not labels or not values:
            return {"success": False, "error": "Missing labels or values"}
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "bar":
            ax.bar(labels, values)
        elif chart_type == "line":
            ax.plot(labels, values, marker='o')
        elif chart_type == "pie":
            ax.pie(values, labels=labels, autopct='%1.1f%%')
        elif chart_type == "scatter":
            ax.scatter(labels, values)
        else:
            ax.bar(labels, values)  # Default to bar
        
        if title:
            ax.set_title(title)
        
        if chart_type != "pie":
            ax.set_xlabel(data.get("xlabel", ""))
            ax.set_ylabel(data.get("ylabel", ""))
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save
        if not output_path:
            output_path = "E:/AgentProject/data/charts/chart.png"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return {
            "success": True,
            "path": output_path,
        }
        
    except Exception as e:
        logger.error(f"Chart creation failed: {e}")
        return {"success": False, "error": str(e)}


def process_excel(
    file_path: str,
    operation: str,
    params: Dict = None
) -> Dict[str, Any]:
    """Process Excel file with various operations.
    
    Args:
        file_path: Path to Excel file
        operation: Operation to perform (read, filter, aggregate, pivot)
        params: Operation parameters
    
    Returns:
        {
            "success": bool,
            "result": str or dict,
            "error": str (if failed)
        }
    """
    try:
        params = params or {}
        
        if operation == "read":
            df = pd.read_excel(file_path, sheet_name=params.get("sheet_name", 0))
            return {
                "success": True,
                "result": df.head(20).to_string(),
                "columns": list(df.columns),
                "shape": df.shape,
            }
        
        elif operation == "filter":
            df = pd.read_excel(file_path)
            column = params.get("column")
            value = params.get("value")
            operator = params.get("operator", "==")
            
            if operator == "==":
                filtered = df[df[column] == value]
            elif operator == ">":
                filtered = df[df[column] > value]
            elif operator == "<":
                filtered = df[df[column] < value]
            elif operator == "contains":
                filtered = df[df[column].str.contains(value, na=False)]
            else:
                filtered = df[df[column] == value]
            
            return {
                "success": True,
                "result": filtered.head(50).to_string(),
                "count": len(filtered),
            }
        
        elif operation == "aggregate":
            df = pd.read_excel(file_path)
            group_by = params.get("group_by")
            agg_column = params.get("agg_column")
            agg_func = params.get("agg_func", "sum")
            
            if group_by and agg_column:
                result = df.groupby(group_by)[agg_column].agg(agg_func)
                return {
                    "success": True,
                    "result": result.to_string(),
                }
            else:
                return {"success": False, "error": "Missing group_by or agg_column"}
        
        elif operation == "pivot":
            df = pd.read_excel(file_path)
            index = params.get("index")
            columns = params.get("columns")
            values = params.get("values")
            aggfunc = params.get("aggfunc", "sum")
            
            pivot = pd.pivot_table(
                df,
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc
            )
            
            return {
                "success": True,
                "result": pivot.to_string(),
            }
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for a list of values."""
    import statistics
    
    if not values:
        return {"error": "Empty list"}
    
    try:
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "mode": statistics.mode(values) if len(set(values)) < len(values) else None,
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "variance": statistics.variance(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
        }
    except Exception as e:
        return {"error": str(e)}

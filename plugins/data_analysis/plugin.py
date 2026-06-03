"""数据分析插件 - 自动分析数据文件并生成洞察"""
from app.agents.plugins import Plugin
import logging

logger = logging.getLogger(__name__)


class DataAnalysisPlugin(Plugin):
    """数据分析插件"""
    
    def __init__(self):
        super().__init__(
            name="data_analysis",
            version="1.0.0",
        )
        self.description = "自动分析CSV、Excel数据文件，生成统计摘要和可视化"
    
    def on_load(self):
        """加载插件时注册工具"""
        
        # 工具1：快速统计
        def quick_stats(file_path: str) -> str:
            """快速统计分析数据文件
            
            Args:
                file_path: 数据文件路径（CSV或Excel）
            
            Returns:
                统计摘要（行数、列数、数据类型、缺失值等）
            """
            try:
                import pandas as pd
                
                # 读取文件
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    return f"不支持的文件格式: {file_path}"
                
                # 生成统计
                stats = []
                stats.append(f"📊 数据概览")
                stats.append(f"- 行数: {len(df)}")
                stats.append(f"- 列数: {len(df.columns)}")
                stats.append(f"- 内存: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
                
                stats.append(f"\n📋 列信息")
                for col in df.columns:
                    dtype = df[col].dtype
                    missing = df[col].isna().sum()
                    stats.append(f"- {col}: {dtype} (缺失: {missing})")
                
                stats.append(f"\n📈 数值列统计")
                numeric = df.select_dtypes(include=['number'])
                if not numeric.empty:
                    stats.append(numeric.describe().to_string())
                
                return "\n".join(stats)
            
            except Exception as e:
                return f"分析失败: {str(e)}"
        
        self.register_tool(
            name="quick_stats",
            func=quick_stats,
            description="快速统计数据文件",
        )
        
        # 工具2：相关性分析
        def correlation_analysis(file_path: str, method: str = "pearson") -> str:
            """相关性分析
            
            Args:
                file_path: 数据文件路径
                method: 相关性方法 (pearson/kendall/spearman)
            
            Returns:
                相关性矩阵
            """
            try:
                import pandas as pd
                
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    return f"不支持的文件格式"
                
                numeric = df.select_dtypes(include=['number'])
                if numeric.empty:
                    return "无数值列可分析"
                
                corr = numeric.corr(method=method)
                
                result = [f"📊 相关性分析 ({method})"]
                result.append(corr.to_string())
                
                # 找出强相关
                strong_corr = []
                for i in range(len(corr.columns)):
                    for j in range(i+1, len(corr.columns)):
                        val = corr.iloc[i, j]
                        if abs(val) > 0.7:
                            strong_corr.append(f"- {corr.columns[i]} <-> {corr.columns[j]}: {val:.3f}")
                
                if strong_corr:
                    result.append(f"\n🔥 强相关性 (>0.7):")
                    result.extend(strong_corr)
                
                return "\n".join(result)
            
            except Exception as e:
                return f"分析失败: {str(e)}"
        
        self.register_tool(
            name="correlation_analysis",
            func=correlation_analysis,
            description="计算数据列相关性",
        )
        
        # 工具3：数据质量检查
        def data_quality_check(file_path: str) -> str:
            """数据质量检查
            
            Args:
                file_path: 数据文件路径
            
            Returns:
                数据质量报告
            """
            try:
                import pandas as pd
                
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    return f"不支持的文件格式"
                
                report = ["📋 数据质量报告"]
                
                # 缺失值
                missing = df.isna().sum()
                missing_pct = (missing / len(df) * 100).round(2)
                
                report.append("\n❌ 缺失值")
                for col in df.columns:
                    if missing[col] > 0:
                        report.append(f"- {col}: {missing[col]} ({missing_pct[col]}%)")
                
                # 重复行
                duplicates = df.duplicated().sum()
                report.append(f"\n🔁 重复行: {duplicates}")
                
                # 异常值（使用IQR）
                report.append("\n⚠️ 可能的异常值")
                numeric = df.select_dtypes(include=['number'])
                for col in numeric.columns:
                    Q1 = numeric[col].quantile(0.25)
                    Q3 = numeric[col].quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = ((numeric[col] < Q1 - 1.5*IQR) | (numeric[col] > Q3 + 1.5*IQR)).sum()
                    if outliers > 0:
                        report.append(f"- {col}: {outliers} 个异常值")
                
                # 建议
                report.append("\n💡 改进建议")
                if missing.sum() > 0:
                    report.append("- 处理缺失值：删除或填充")
                if duplicates > 0:
                    report.append("- 删除重复行")
                
                return "\n".join(report)
            
            except Exception as e:
                return f"检查失败: {str(e)}"
        
        self.register_tool(
            name="data_quality_check",
            func=data_quality_check,
            description="检查数据质量",
        )
        
        logger.info(f"Plugin {self.name} loaded with {len(self.tools)} tools")
    
    def on_unload(self):
        """卸载插件"""
        logger.info(f"Plugin {self.name} unloaded")


# 插件元数据
PLUGIN_INFO = {
    "name": "data_analysis",
    "version": "1.0.0",
    "description": "数据分析插件 - 自动分析数据文件并生成洞察",
    "author": "AI Agent",
    "enabled": True,
    "tools": ["quick_stats", "correlation_analysis", "data_quality_check"],
    "hooks": [],
}

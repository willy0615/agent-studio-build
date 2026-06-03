"""生成学习效果监控报告"""
import sys
sys.path.insert(0, ".")

from datetime import datetime, timedelta
from pathlib import Path

print("=" * 70)
print("Agent学习效果监控报告")
print("=" * 70)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 模拟数据（实际使用时从learning_evaluator获取）
report_data = {
    "period": "2026-06-03",
    "total_tasks": 25,
    "successful_tasks": 23,
    "failed_tasks": 2,
    "success_rate": 92.0,
    "avg_execution_time_ms": 1250,
    "tool_usage": {
        "quick_stats": {"calls": 15, "success": 14, "avg_time": 800},
        "web_search": {"calls": 10, "success": 10, "avg_time": 1200},
        "analyze_code": {"calls": 8, "success": 7, "avg_time": 600},
        "write_file": {"calls": 12, "success": 12, "avg_time": 50},
    },
    "errors": [
        {"type": "TimeoutError", "count": 1},
        {"type": "ValueError", "count": 1},
    ],
}

# 输出报告
print("## 总体表现")
print(f"- 评估日期: {report_data['period']}")
print(f"- 总任务数: {report_data['total_tasks']}")
print(f"- 成功任务: {report_data['successful_tasks']}")
print(f"- 失败任务: {report_data['failed_tasks']}")
print(f"- 成功率: {report_data['success_rate']}%")
print(f"- 平均执行时间: {report_data['avg_execution_time_ms']}ms")
print()

# 工具性能
print("## 工具性能分析")
print()
print("| 工具 | 调用次数 | 成功率 | 平均时间 |")
print("|------|---------|--------|----------|")

for tool, stats in report_data["tool_usage"].items():
    success_rate = (stats["success"] / stats["calls"] * 100) if stats["calls"] > 0 else 0
    print(f"| {tool} | {stats['calls']} | {success_rate:.1f}% | {stats['avg_time']}ms |")

print()

# 错误分析
print("## 错误分析")
print()
for error in report_data["errors"]:
    print(f"- {error['type']}: {error['count']} 次")
print()

# 改进建议
print("## 改进建议")
print()
print("1. [OK] 成功率92%表现良好，继续保持")
print("2. [FIX] quick_stats工具有1次失败，建议检查文件格式处理")
print("3. [OPT] 平均执行时间1.25秒，可考虑优化慢速工具")
print("4. [REC] 建议启用LLM缓存以提升响应速度")
print()

# 趋势预测
print("## 趋势预测")
print()
print("基于当前数据预测：")
print("- [UP] 成功率将稳定在90%以上")
print("- [UP] 预计下周任务量增长20%")
print("- [REC] 建议增加错误重试机制")
print()

print("=" * 70)
print("报告生成完成")
print("=" * 70)

# 保存到文件
output_dir = Path("E:/AgentProject/reports")
output_dir.mkdir(exist_ok=True)

report_file = output_dir / f"learning_report_{datetime.now().strftime('%Y%m%d')}.md"

with open(report_file, 'w', encoding='utf-8') as f:
    f.write(f"""# Agent学习效果监控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 总体表现

| 指标 | 数值 |
|------|------|
| 评估日期 | {report_data['period']} |
| 总任务数 | {report_data['total_tasks']} |
| 成功任务 | {report_data['successful_tasks']} |
| 失败任务 | {report_data['failed_tasks']} |
| 成功率 | {report_data['success_rate']}% |
| 平均执行时间 | {report_data['avg_execution_time_ms']}ms |

---

## 工具性能分析

| 工具 | 调用次数 | 成功率 | 平均时间 |
|------|---------|--------|----------|
""")

    for tool, stats in report_data["tool_usage"].items():
        success_rate = (stats["success"] / stats["calls"] * 100) if stats["calls"] > 0 else 0
        f.write(f"| {tool} | {stats['calls']} | {success_rate:.1f}% | {stats['avg_time']}ms |\n")

    f.write("""
---

## 错误分析

""")
    for error in report_data["errors"]:
        f.write(f"- {error['type']}: {error['count']} 次\n")

    f.write("""
---

## 改进建议

1. [OK] 成功率92%表现良好，继续保持
2. [FIX] quick_stats工具有1次失败，建议检查文件格式处理
3. [OPT] 平均执行时间1.25秒，可考虑优化慢速工具
4. [REC] 建议启用LLM缓存以提升响应速度

---

## 趋势预测

基于当前数据预测：
- [UP] 成功率将稳定在90%以上
- [UP] 预计下周任务量增长20%
- [REC] 建议增加错误重试机制

---

**报告生成完成**
""")

print(f"\n✅ 报告已保存至: {report_file}")

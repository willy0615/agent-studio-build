#!/usr/bin/env python3
"""检查PyQt6依赖"""
import sys

missing = []
try:
    import PyQt6
    print(f"✅ PyQt6 {PyQt6.QtCore.PYQT_VERSION_STR}")
except ImportError:
    missing.append("PyQt6")

try:
    import qfluentwidgets
    print(f"✅ PyQt-Fluent-Widgets")
except ImportError:
    missing.append("PyQt-Fluent-Widgets")

if missing:
    print(f"\n❌ 缺少依赖: {', '.join(missing)}")
    print("安装命令: pip install PyQt6 PyQt-Fluent-Widgets")
    sys.exit(1)
else:
    print("\n✅ 所有依赖已安装")
    sys.exit(0)

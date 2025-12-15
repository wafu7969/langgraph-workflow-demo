#!/usr/bin/env python3
"""
LangGraph 旅游规划系统 - 主程序入口

使用方法:
    python run.py

这个文件是项目的主入口点，会自动导入 src/ 目录中的模块。
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 导入主程序
from main import main

if __name__ == "__main__":
    main()
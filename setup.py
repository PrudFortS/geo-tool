#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="geo-tool",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pandas",
        "lxml"
    ],
    entry_points={
        "console_scripts": [
            "geo-tool=geo_tool.cli:main",
        ],
    },
    author="PrudFortS",
    description="GEO/ENA 数据下载与处理工具",
    long_description="""
GEO Tool 是一个用于下载和处理 GEO/ENA 数据的命令行工具。

功能特点：
- 支持从 GEO（SRA）和 ENA（ascp）下载数据
- 支持并发下载和转换
- 支持时间控制（只在指定时段运行）
- 实时记录任务状态到 JSON 文件
- 支持暂停/恢复功能
    """,
    long_description_content_type="text/markdown",
    url="https://github.com/PrudFortS/geo-tool",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)

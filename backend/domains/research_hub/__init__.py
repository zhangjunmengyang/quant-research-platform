"""
Research Hub - 研报知识库

提供研报入库、RAG 检索和 ChatBot 对话功能。

架构设计:
- 模块化 RAG 组件，支持灵活替换和对比实验
- 配置驱动的流水线，通过 YAML 定义 RAG 流程
- 为 Agentic RAG 预留扩展点
"""

__version__ = "0.1.0"

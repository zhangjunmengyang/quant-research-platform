"""
MinerU PDF 解析器

使用 MinerU 2.5 模型进行 PDF 解析，支持:
- 高精度文本提取
- 表格结构识别
- 公式识别
- 多语言 OCR
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import tempfile
import shutil

from ..base.parser import BaseParser, ParsedDocument, ContentType
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@dataclass
class MinerUConfig:
    """MinerU 配置"""
    version: str = "2.5"
    ocr_lang: str = "ch_sim+en"
    table_structure: bool = True
    formula_recognition: bool = True
    output_format: str = "markdown"  # markdown / json / html
    # MinerU 命令路径
    magic_pdf_path: str = "magic-pdf"


@component_registries.parser.register("mineru")
class MinerUParser(BaseParser):
    """
    MinerU PDF 解析器

    使用 MinerU (magic-pdf) 命令行工具进行解析。
    要求系统已安装 magic-pdf。

    安装方式:
        pip install magic-pdf[full]

    使用示例:
        parser = MinerUParser(version="2.5", ocr_lang="ch_sim+en")
        result = await parser.parse(pdf_path)
    """

    def __init__(
        self,
        version: str = "2.5",
        ocr_lang: str = "ch_sim+en",
        table_structure: bool = True,
        formula_recognition: bool = True,
        output_format: str = "markdown",
        magic_pdf_path: str = "magic-pdf",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.mineru_config = MinerUConfig(
            version=version,
            ocr_lang=ocr_lang,
            table_structure=table_structure,
            formula_recognition=formula_recognition,
            output_format=output_format,
            magic_pdf_path=magic_pdf_path,
        )

    async def setup(self) -> None:
        """验证 MinerU 是否可用"""
        try:
            result = subprocess.run(
                [self.mineru_config.magic_pdf_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info(f"MinerU version: {result.stdout.strip()}")
            else:
                logger.warning(
                    f"MinerU check failed: {result.stderr}. "
                    "Will fall back to basic parsing if needed."
                )
        except FileNotFoundError:
            logger.warning(
                "magic-pdf not found. Please install: pip install magic-pdf[full]"
            )
        except subprocess.TimeoutExpired:
            logger.warning("MinerU version check timed out")

    async def parse(self, source: str) -> ParsedDocument:
        """
        解析 PDF 文件

        Args:
            source: PDF 文件路径

        Returns:
            ParsedDocument 包含解析后的内容
        """
        pdf_path = Path(source)
        if not pdf_path.exists():
            return ParsedDocument(
                content="",
                content_type=ContentType.TEXT,
                metadata={"error": f"File not found: {source}"},
                success=False,
                error=f"File not found: {source}",
            )

        # 创建临时输出目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            try:
                # 调用 magic-pdf 命令
                result = await self._run_magic_pdf(pdf_path, output_dir)

                if not result["success"]:
                    return ParsedDocument(
                        content="",
                        content_type=ContentType.TEXT,
                        metadata={"error": result["error"]},
                        success=False,
                        error=result["error"],
                    )

                # 读取解析结果
                content, metadata = self._read_output(output_dir, pdf_path.stem)

                return ParsedDocument(
                    content=content,
                    content_type=ContentType.MARKDOWN,
                    metadata=metadata,
                    source_path=str(pdf_path),
                    page_count=metadata.get("page_count", 0),
                    success=True,
                )

            except Exception as e:
                logger.error(f"MinerU parse error: {e}", exc_info=True)
                return ParsedDocument(
                    content="",
                    content_type=ContentType.TEXT,
                    metadata={"error": str(e)},
                    success=False,
                    error=str(e),
                )

    async def _run_magic_pdf(
        self, pdf_path: Path, output_dir: Path
    ) -> Dict[str, Any]:
        """
        运行 magic-pdf 命令

        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录

        Returns:
            包含 success 和 error 的字典
        """
        import asyncio

        # 构建命令
        cmd = [
            self.mineru_config.magic_pdf_path,
            "-p", str(pdf_path),
            "-o", str(output_dir),
            "-m", "auto",  # 自动选择模式
        ]

        logger.info(f"Running MinerU: {' '.join(cmd)}")

        try:
            # 异步运行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300,  # 5 分钟超时
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"MinerU failed: {error_msg}")
                return {"success": False, "error": error_msg}

            return {"success": True, "error": None}

        except asyncio.TimeoutError:
            logger.error("MinerU parsing timeout (300s)")
            return {"success": False, "error": "Parsing timeout"}
        except Exception as e:
            logger.error(f"MinerU execution error: {e}")
            return {"success": False, "error": str(e)}

    def _read_output(
        self, output_dir: Path, pdf_stem: str
    ) -> tuple[str, Dict[str, Any]]:
        """
        读取 MinerU 输出结果

        Args:
            output_dir: 输出目录
            pdf_stem: PDF 文件名（不含扩展名）

        Returns:
            (content, metadata) 元组
        """
        metadata = {}

        # MinerU 输出结构: output_dir/pdf_stem/auto/pdf_stem.md
        md_path = output_dir / pdf_stem / "auto" / f"{pdf_stem}.md"
        json_path = output_dir / pdf_stem / "auto" / "content_list.json"

        # 尝试读取 Markdown 内容
        content = ""
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            logger.info(f"Read markdown content: {len(content)} chars")
        else:
            # 尝试其他可能的路径
            for md_file in output_dir.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                logger.info(f"Found markdown at: {md_file}")
                break

        # 尝试读取结构化元数据
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    content_list = json.load(f)
                metadata["content_list"] = content_list
                metadata["page_count"] = self._count_pages(content_list)
            except json.JSONDecodeError:
                logger.warning("Failed to parse content_list.json")

        # 统计表格和公式
        metadata["has_tables"] = "| --- |" in content or "<table" in content.lower()
        metadata["has_formulas"] = "$$" in content or "$" in content
        metadata["char_count"] = len(content)

        return content, metadata

    def _count_pages(self, content_list: List[Dict]) -> int:
        """从 content_list 统计页数"""
        pages = set()
        for item in content_list:
            if "page_idx" in item:
                pages.add(item["page_idx"])
        return len(pages) if pages else 0


# 回退解析器（当 MinerU 不可用时）
@component_registries.parser.register("basic")
class BasicPDFParser(BaseParser):
    """
    基础 PDF 解析器

    使用 PyMuPDF (fitz) 进行简单的文本提取。
    作为 MinerU 不可用时的回退方案。
    """

    async def parse(self, source: str) -> ParsedDocument:
        """
        基础 PDF 文本提取

        Args:
            source: PDF 文件路径

        Returns:
            ParsedDocument
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return ParsedDocument(
                content="",
                content_type=ContentType.TEXT,
                success=False,
                error="PyMuPDF not installed. Run: pip install pymupdf",
            )

        pdf_path = Path(source)
        if not pdf_path.exists():
            return ParsedDocument(
                content="",
                content_type=ContentType.TEXT,
                success=False,
                error=f"File not found: {source}",
            )

        try:
            doc = fitz.open(str(pdf_path))
            pages = []

            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                pages.append(f"## Page {page_num + 1}\n\n{text}")

            content = "\n\n".join(pages)

            return ParsedDocument(
                content=content,
                content_type=ContentType.MARKDOWN,
                source_path=str(pdf_path),
                page_count=len(doc),
                metadata={
                    "parser": "basic",
                    "char_count": len(content),
                },
                success=True,
            )

        except Exception as e:
            logger.error(f"Basic PDF parse error: {e}")
            return ParsedDocument(
                content="",
                content_type=ContentType.TEXT,
                success=False,
                error=str(e),
            )
        finally:
            if "doc" in locals():
                doc.close()

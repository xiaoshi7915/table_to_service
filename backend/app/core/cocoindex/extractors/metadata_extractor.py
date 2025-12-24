"""
元数据提取器
从文档中提取标题、作者、创建时间等元数据
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger

from app.core.llm.base import BaseLLMClient


class MetadataExtractor:
    """元数据提取器"""
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """
        初始化元数据提取器
        
        Args:
            llm_client: LLM 客户端（用于智能提取，可选）
        """
        self.llm_client = llm_client
    
    def extract(
        self,
        document_data: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提取文档元数据
        
        Args:
            document_data: 文档数据（来自解析器）
            file_path: 文件路径（可选）
            
        Returns:
            元数据字典
        """
        metadata = {}
        
        # 1. 从解析器结果中提取元数据
        if "metadata" in document_data:
            metadata.update(document_data["metadata"])
        
        # 2. 从文件路径提取信息
        if file_path:
            file_info = self._extract_file_info(file_path)
            metadata.update(file_info)
        
        # 3. 从文档内容中提取（如果元数据不完整）
        if not metadata.get("title") and document_data.get("text"):
            title = self._extract_title_from_content(document_data["text"])
            if title:
                metadata["title"] = title
        
        # 4. 使用 LLM 提取关键信息（如果可用）
        if self.llm_client and document_data.get("text"):
            llm_metadata = self._extract_with_llm(document_data["text"])
            if llm_metadata:
                metadata.update(llm_metadata)
        
        return metadata
    
    def _extract_file_info(self, file_path: str) -> Dict[str, Any]:
        """从文件路径提取信息"""
        path = Path(file_path)
        
        info = {
            "filename": path.name,
            "file_extension": path.suffix.lower(),
            "file_stem": path.stem,
        }
        
        # 尝试从文件名推断分类和标签
        stem_lower = path.stem.lower()
        
        # 分类推断（简单规则）
        if any(keyword in stem_lower for keyword in ['手册', 'manual', 'guide']):
            info["category"] = "手册"
        elif any(keyword in stem_lower for keyword in ['规范', 'spec', 'standard']):
            info["category"] = "规范"
        elif any(keyword in stem_lower for keyword in ['报告', 'report']):
            info["category"] = "报告"
        elif any(keyword in stem_lower for keyword in ['文档', 'doc', 'documentation']):
            info["category"] = "文档"
        
        return info
    
    def _extract_title_from_content(self, text: str) -> Optional[str]:
        """从内容中提取标题"""
        if not text:
            return None
        
        lines = text.split('\n')
        
        # 检查前几行
        for line in lines[:10]:
            line = line.strip()
            if not line:
                continue
            
            # 跳过太长的行（不太可能是标题）
            if len(line) > 200:
                continue
            
            # 跳过看起来像代码的行
            if line.startswith(('```', 'import', 'from', 'def ', 'class ')):
                continue
            
            # 如果行较短且包含中文字符，可能是标题
            if len(line) < 100 and any('\u4e00' <= char <= '\u9fff' for char in line):
                return line
        
        return None
    
    def _extract_with_llm(self, text: str) -> Dict[str, Any]:
        """使用 LLM 提取关键信息"""
        if not self.llm_client:
            return {}
        
        try:
            # 只使用前2000字符（避免token过多）
            preview_text = text[:2000] if len(text) > 2000 else text
            
            prompt = f"""请从以下文档内容中提取关键信息，返回JSON格式：
- title: 文档标题
- category: 文档分类（如：手册、规范、报告、文档等）
- tags: 文档标签（数组，3-5个关键词）
- summary: 文档摘要（50字以内）

文档内容：
{preview_text}

请只返回JSON格式，不要包含其他解释。"""
            
            # LLMClient 使用异步方法，这里需要同步调用
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            messages = [{"role": "user", "content": prompt}]
            response_dict = loop.run_until_complete(
                self.llm_client.chat_completion(messages, max_tokens=200)
            )
            response = response_dict.get("content", "")
            
            # 尝试解析JSON响应
            import json
            try:
                # 移除可能的markdown代码块标记
                response_text = response.strip()
                if response_text.startswith('```'):
                    # 提取JSON部分
                    lines = response_text.split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.strip().startswith('```'):
                            in_json = not in_json
                            continue
                        if in_json:
                            json_lines.append(line)
                    response_text = '\n'.join(json_lines)
                
                metadata = json.loads(response_text)
                return metadata
            except json.JSONDecodeError:
                logger.warning(f"LLM返回的不是有效JSON: {response}")
                return {}
        except Exception as e:
            logger.warning(f"使用LLM提取元数据失败: {e}")
            return {}
    
    def extract_categories_and_tags(
        self,
        text: str,
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        提取分类和标签
        
        Args:
            text: 文档文本
            existing_metadata: 已有元数据
            
        Returns:
            包含category和tags的字典
        """
        result = {}
        
        # 如果已有分类和标签，直接返回
        if existing_metadata:
            if "category" in existing_metadata:
                result["category"] = existing_metadata["category"]
            if "tags" in existing_metadata:
                result["tags"] = existing_metadata["tags"]
        
        # 如果缺少分类，尝试从内容推断
        if "category" not in result:
            category = self._infer_category(text)
            if category:
                result["category"] = category
        
        # 如果缺少标签，尝试从内容提取关键词
        if "tags" not in result:
            tags = self._extract_keywords(text)
            if tags:
                result["tags"] = tags
        
        return result
    
    def _infer_category(self, text: str) -> Optional[str]:
        """从内容推断分类"""
        text_lower = text.lower()
        
        # 简单的关键词匹配
        category_keywords = {
            "手册": ["手册", "manual", "guide", "使用说明", "操作指南"],
            "规范": ["规范", "spec", "standard", "标准", "规定"],
            "报告": ["报告", "report", "分析", "总结"],
            "文档": ["文档", "doc", "documentation", "说明"],
            "API": ["api", "接口", "endpoint", "rest", "graphql"],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return None
    
    def _extract_keywords(self, text: str, max_tags: int = 5) -> List[str]:
        """从内容提取关键词"""
        # 简单的关键词提取（实际应用中可以使用更复杂的NLP方法）
        # 这里只是示例，实际应该使用更专业的提取方法
        
        # 移除标点符号和常见停用词
        import re
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', text)
        
        # 统计词频（简化版）
        from collections import Counter
        word_freq = Counter(words)
        
        # 返回最常见的词
        common_words = word_freq.most_common(max_tags * 2)
        
        # 过滤太短的词
        tags = [word for word, freq in common_words if len(word) >= 2][:max_tags]
        
        return tags


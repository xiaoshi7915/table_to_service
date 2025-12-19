"""
嵌入向量生成服务
支持多种嵌入模型（OpenAI、本地模型等）
"""
from typing import List, Optional
from loguru import logger
import os


class EmbeddingService:
    """嵌入向量生成服务"""
    
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """
        初始化嵌入服务
        
        Args:
            model_name: 嵌入模型名称
            api_key: API密钥（如果使用OpenAI）
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
    
    def _get_client(self):
        """获取OpenAI客户端（懒加载）"""
        if self._client is None:
            try:
                from openai import OpenAI
                if not self.api_key:
                    raise ValueError("未设置OPENAI_API_KEY环境变量")
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装openai库: pip install openai")
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本的嵌入向量
        
        Args:
            text: 文本内容
            
        Returns:
            嵌入向量列表
        """
        try:
            # 使用OpenAI的嵌入模型
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}", exc_info=True)
            # 降级方案：返回零向量（实际应用中应该使用本地模型）
            logger.warning("使用零向量作为降级方案")
            return [0.0] * 1536  # OpenAI text-embedding-3-small 的维度
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"批量生成嵌入向量失败: {e}", exc_info=True)
            # 降级方案：逐个生成
            return [self.generate_embedding(text) for text in texts]


class LocalEmbeddingService:
    """
    本地嵌入服务（可选）
    使用 sentence-transformers 或其他本地模型
    """
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化本地嵌入服务
        
        Args:
            model_name: 本地模型名称
        """
        self.model_name = model_name
        self._model = None
    
    def _get_model(self):
        """获取模型（懒加载）"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError("请安装sentence-transformers库: pip install sentence-transformers")
        return self._model
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本的嵌入向量
        
        Args:
            text: 文本内容
            
        Returns:
            嵌入向量列表
        """
        try:
            model = self._get_model()
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"本地模型生成嵌入向量失败: {e}", exc_info=True)
            return [0.0] * 384  # 默认维度
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            model = self._get_model()
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"本地模型批量生成嵌入向量失败: {e}", exc_info=True)
            return [self.generate_embedding(text) for text in texts]



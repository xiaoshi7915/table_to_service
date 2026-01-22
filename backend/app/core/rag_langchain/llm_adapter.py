"""
LLM适配器
将我们的LLM客户端适配为LangChain兼容格式
"""
from typing import Any, List, Optional
import json
import time
try:
    # LangChain 1.x
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
    from langchain_core.callbacks.manager import CallbackManagerForLLMRun
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.base_language import BaseLanguageModel
    from langchain.schema import BaseMessage, AIMessage, HumanMessage
    from langchain.callbacks.manager import CallbackManagerForLLMRun
from loguru import logger

from app.core.llm.base import BaseLLMClient


class LangChainLLMAdapter(BaseLanguageModel):
    """LangChain LLM适配器"""
    
    # 将llm_client存储为实例属性，不使用Pydantic字段（避免序列化问题）
    _llm_client: Optional[BaseLLMClient] = None
    
    def __init__(self, llm_client: BaseLLMClient, **kwargs):
        """
        初始化适配器
        
        Args:
            llm_client: 我们的LLM客户端
        """
        # 先调用父类初始化
        super().__init__(**kwargs)
        # 然后设置实例属性（不使用Pydantic字段）
        object.__setattr__(self, '_llm_client', llm_client)
    
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Any:
        """
        生成文本（LangChain接口）
        
        Args:
            prompts: 提示词列表
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            LLMResult对象
        """
        try:
            from langchain_core.outputs import LLMResult, Generation
        except ImportError:
            from langchain.schema import LLMResult, Generation
        
        generations = []
        
        for prompt in prompts:
            try:
                # 调用我们的LLM客户端
                import asyncio
                
                # 构建消息
                messages = [{"role": "user", "content": prompt}]
                
                # 调用异步方法
                llm_client = getattr(self, '_llm_client', None)
                if not llm_client:
                    raise AttributeError("llm_client not initialized")
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，使用同步方式
                        response = self._call_sync(messages)
                    else:
                        response = loop.run_until_complete(
                            llm_client.chat_completion(messages)
                        )
                except RuntimeError:
                    # 没有事件循环，创建新的
                    response = asyncio.run(
                        llm_client.chat_completion(messages)
                    )
                
                # 提取内容
                if isinstance(response, dict):
                    content = response.get("content", "")
                else:
                    content = str(response)
                
                generations.append([Generation(text=content)])
                
            except Exception as e:
                logger.error("LLM生成失败: %s", str(e), exc_info=True)
                generations.append([Generation(text=f"生成失败: {str(e)}")])
        
        return LLMResult(generations=generations)
    
    def _call_sync(self, messages: List[dict]) -> dict:
        """同步调用（降级方案）"""
        llm_client = getattr(self, '_llm_client', None)
        if not llm_client:
            logger.warning("LLM客户端未初始化")
            return {"content": "LLM客户端未初始化"}
        
        try:
            import asyncio
            # 检查是否有运行中的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行中的循环，需要在新线程中运行
                import concurrent.futures
                
                def run_llm_call():
                    """在新线程中运行LLM调用"""
                    return asyncio.run(llm_client.chat_completion(messages))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_llm_call)
                    try:
                        result = future.result(timeout=30)
                        return result
                    except Exception as future_exc:
                        # 重新抛出异常，让外层处理
                        raise
            except RuntimeError:
                # 没有运行中的循环，直接使用asyncio.run
                result = asyncio.run(llm_client.chat_completion(messages))
                return result
        except Exception as e:
            # 使用 %s 格式化避免 loguru 解析错误消息中的占位符
            logger.error("LLM同步调用失败: %s", str(e), exc_info=True)
            # 提取更友好的错误信息
            error_msg = str(e)
            if "Authentication" in error_msg or "401" in error_msg or "invalid" in error_msg.lower():
                error_msg = "API密钥无效或已过期，请检查AI模型配置"
            elif "timeout" in error_msg.lower():
                error_msg = "LLM调用超时，请稍后重试"
            return {"content": f"LLM调用失败: {error_msg}"}
    
    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Any:
        """
        异步生成文本
        
        Args:
            prompts: 提示词列表
            stop: 停止词列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            LLMResult对象
        """
        try:
            from langchain_core.outputs import LLMResult, Generation
        except ImportError:
            from langchain.schema import LLMResult, Generation
        
        generations = []
        
        for prompt in prompts:
            try:
                messages = [{"role": "user", "content": prompt}]
                llm_client = getattr(self, '_llm_client', None)
                if not llm_client:
                    raise AttributeError("llm_client not initialized")
                response = await llm_client.chat_completion(messages)
                
                if isinstance(response, dict):
                    content = response.get("content", "")
                else:
                    content = str(response)
                
                generations.append([Generation(text=content)])
                
            except Exception as e:
                logger.error("LLM异步生成失败: %s", str(e), exc_info=True)
                generations.append([Generation(text=f"生成失败: {str(e)}")])
        
        return LLMResult(generations=generations)
    
    @property
    def _llm_type(self) -> str:
        """LLM类型"""
        llm_client = getattr(self, '_llm_client', None)
        if llm_client:
            return f"{llm_client.__class__.__name__}_adapter"
        return "unknown_adapter"
    
    def generate_prompt(
        self,
        prompts: List[Any],
        stop: Optional[List[str]] = None,
        callbacks: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """生成提示词（LangChain 1.x要求）"""
        return self._generate(prompts, stop=stop, run_manager=callbacks, **kwargs)
    
    async def agenerate_prompt(
        self,
        prompts: List[Any],
        stop: Optional[List[str]] = None,
        callbacks: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """异步生成提示词（LangChain 1.x要求）"""
        return await self._agenerate(prompts, stop=stop, run_manager=callbacks, **kwargs)
    
    def invoke(self, input: str, config: Optional[dict] = None, **kwargs) -> Any:
        """
        LangChain标准invoke接口
        
        Args:
            input: 输入文本
            config: 配置
            **kwargs: 其他参数
            
        Returns:
            AIMessage对象
        """
        try:
            messages = [{"role": "user", "content": input}]
            
            import asyncio
            llm_client = getattr(self, '_llm_client', None)
            if not llm_client:
                return AIMessage(content="LLM客户端未初始化")
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    response = self._call_sync(messages)
                else:
                    response = loop.run_until_complete(
                        llm_client.chat_completion(messages)
                    )
            except RuntimeError:
                response = asyncio.run(
                    llm_client.chat_completion(messages)
                )
            
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            return AIMessage(content=content)
            
        except Exception as e:
            logger.error("invoke失败: %s", str(e), exc_info=True)
            return AIMessage(content=f"调用失败: {str(e)}")
    
    def predict(self, text: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        """
        LangChain 0.x 要求的 predict 方法（同步）
        
        Args:
            text: 输入文本
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        try:
            messages = [{"role": "user", "content": text}]
            llm_client = getattr(self, '_llm_client', None)
            if not llm_client:
                return "LLM客户端未初始化"
            
            response = self._call_sync(messages)
            
            if isinstance(response, dict):
                return response.get("content", "")
            else:
                return str(response)
        except Exception as e:
            logger.error("predict失败: %s", str(e), exc_info=True)
            return f"预测失败: {str(e)}"
    
    async def apredict(self, text: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        """
        LangChain 0.x 要求的 apredict 方法（异步）
        
        Args:
            text: 输入文本
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        try:
            messages = [{"role": "user", "content": text}]
            llm_client = getattr(self, '_llm_client', None)
            if not llm_client:
                return "LLM客户端未初始化"
            
            response = await llm_client.chat_completion(messages)
            
            if isinstance(response, dict):
                return response.get("content", "")
            else:
                return str(response)
        except Exception as e:
            logger.error("apredict失败: %s", str(e), exc_info=True)
            return f"异步预测失败: {str(e)}"
    
    def predict_messages(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        """
        LangChain 1.x 要求的 predict_messages 方法（同步）
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            AIMessage对象
        """
        try:
            # 将LangChain消息转换为我们的格式
            formatted_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    role = "user"
                    if isinstance(msg, AIMessage):
                        role = "assistant"
                    formatted_messages.append({"role": role, "content": msg.content})
            
            llm_client = getattr(self, '_llm_client', None)
            if not llm_client:
                return AIMessage(content="LLM客户端未初始化")
            
            response = self._call_sync(formatted_messages)
            
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            return AIMessage(content=content)
        except Exception as e:
            logger.error("predict_messages失败: %s", str(e), exc_info=True)
            return AIMessage(content=f"预测消息失败: {str(e)}")
    
    async def apredict_messages(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        """
        LangChain 1.x 要求的 apredict_messages 方法（异步）
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            AIMessage对象
        """
        try:
            # 将LangChain消息转换为我们的格式
            formatted_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    role = "user"
                    if isinstance(msg, AIMessage):
                        role = "assistant"
                    formatted_messages.append({"role": role, "content": msg.content})
            
            llm_client = getattr(self, '_llm_client', None)
            if not llm_client:
                return AIMessage(content="LLM客户端未初始化")
            
            response = await llm_client.chat_completion(formatted_messages)
            
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            return AIMessage(content=content)
        except Exception as e:
            logger.error("apredict_messages失败: %s", str(e), exc_info=True)
            return AIMessage(content=f"异步预测消息失败: {str(e)}")



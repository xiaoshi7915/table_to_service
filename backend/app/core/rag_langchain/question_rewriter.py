"""
用户提问改写服务
使用LLM或规则引擎优化问题表述，提高SQL生成准确性
"""
from typing import Optional, Dict, Any
from loguru import logger
import re


class QuestionRewriter:
    """用户提问改写服务"""
    
    def __init__(self, llm_client=None):
        """
        初始化问题改写服务
        
        Args:
            llm_client: LLM客户端（可选，如果为None则使用规则引擎）
        """
        self.llm_client = llm_client
    
    def rewrite_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        改写用户问题，优化表述
        
        Args:
            question: 原始问题
            context: 上下文信息（可选），包含：
                - db_type: 数据库类型
                - table_names: 表名列表
                - terminology_map: 术语映射
            
        Returns:
            包含改写后问题和元信息的字典：
            {
                "original_question": "原始问题",
                "rewritten_question": "改写后的问题",
                "changes": ["变更说明"],
                "method": "llm" | "rule",
                "warnings": ["警告信息"]  # 新增：权限和隐私警告
            }
        """
        if not question or not question.strip():
            return {
                "original_question": question,
                "rewritten_question": question,
                "changes": [],
                "method": "none",
                "warnings": []
            }
        
        warnings = []
        
        # 检测是否涉及查询所有数据明细
        query_all_patterns = [
            r'查询.*所有.*数据',
            r'查看.*所有.*记录',
            r'显示.*全部.*信息',
            r'列出.*所有.*明细',
            r'所有.*数据.*明细',
            r'全部.*数据'
        ]
        
        for pattern in query_all_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                warnings.append("为了数据安全和性能考虑，系统不允许查询所有数据明细。建议使用统计查询（如COUNT、SUM等）或添加筛选条件。")
                break
        
        # 检测是否涉及修改数据操作
        modify_patterns = [
            r'删除|删除数据|删除记录',
            r'修改|更新|更改数据',
            r'插入|添加|新增数据',
            r'清空|清空数据|清空表'
        ]
        
        for pattern in modify_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                warnings.append("您没有权限执行修改数据的操作。系统只支持查询操作，请使用SELECT查询语句。")
                break
        
        # 优先使用LLM改写（如果可用）
        if self.llm_client:
            try:
                result = self._rewrite_with_llm(question, context)
                # 确保返回结果包含warnings
                if "warnings" not in result:
                    result["warnings"] = warnings
                return result
            except Exception as e:
                logger.warning(f"LLM改写失败: {e}，降级到规则引擎")
        
        # 使用规则引擎改写（传递warnings）
        return self._rewrite_with_rules(question, context, warnings)
    
    def _rewrite_with_llm(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        warnings: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        使用LLM改写问题
        
        Args:
            question: 原始问题
            context: 上下文信息
            warnings: 警告列表（可选）
            
        Returns:
            改写结果
        """
        # 构建提示词
        prompt = f"""请优化以下用户问题，使其更清晰、具体，便于生成准确的SQL查询。

原始问题：{question}

"""
        
        if context:
            if context.get("table_names"):
                prompt += f"可用表名：{', '.join(context['table_names'][:10])}\n"
            if context.get("db_type"):
                prompt += f"数据库类型：{context['db_type']}\n"
        
        prompt += """
优化要求：
1. 保持原意不变
2. 补充缺失的关键信息（如时间范围、筛选条件等）
3. 规范化术语和表述
4. 如果问题模糊，添加合理的假设说明
5. 确保问题可以直接用于SQL生成

只返回优化后的问题，不要包含其他解释："""
        
        # 调用LLM（异步方法，需要await）
        # 注意：这里暂时跳过LLM改写，因为需要异步调用
        # 可以在调用方使用async/await，或者创建异步版本
        logger.info("LLM改写功能需要异步调用，暂时使用规则引擎")
        return self._rewrite_with_rules(question, context, warnings or [])
    
    def _rewrite_with_rules(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用规则引擎改写问题
        
        Args:
            question: 原始问题
            context: 上下文信息
            
        Returns:
            改写结果
        """
        original_question = question
        rewritten_question = question
        changes = []
        
        # 1. 规范化常见表述
        replacements = {
            # 时间相关
            r'最近\s*(\d+)\s*天': r'最近\1天',
            r'最近\s*(\d+)\s*个月': r'最近\1个月',
            r'最近\s*(\d+)\s*年': r'最近\1年',
            # 数量相关
            r'有多少': '统计数量',
            r'多少个': '统计数量',
            r'几条': '统计数量',
            # 查询相关
            r'看看': '查询',
            r'查一下': '查询',
            r'给我': '查询',
            # 统计相关
            r'汇总': '统计汇总',
            r'合计': '统计合计',
        }
        
        for pattern, replacement in replacements.items():
            if re.search(pattern, rewritten_question, re.IGNORECASE):
                rewritten_question = re.sub(pattern, replacement, rewritten_question, flags=re.IGNORECASE)
                changes.append(f"规范化表述：{pattern} -> {replacement}")
        
        # 2. 补充缺失的时间范围（如果问题涉及时间但没有指定范围）
        time_keywords = ['时间', '日期', '创建', '更新', '最近', '今天', '昨天', '本周', '本月', '今年']
        has_time_keyword = any(keyword in rewritten_question for keyword in time_keywords)
        
        if has_time_keyword and not re.search(r'(最近|今天|昨天|本周|本月|今年|\d{4})', rewritten_question):
            # 如果提到时间但没有具体范围，添加"最近"作为默认
            if '时间' in rewritten_question or '日期' in rewritten_question:
                rewritten_question = rewritten_question.replace('时间', '最近的时间').replace('日期', '最近的日期')
                changes.append("补充时间范围：添加'最近'作为默认范围")
        
        # 3. 术语替换（如果有术语映射）
        if context and context.get("terminology_map"):
            terminology_map = context["terminology_map"]
            for term, db_field in terminology_map.items():
                if term in rewritten_question:
                    # 在问题中同时保留术语和字段名，便于理解
                    rewritten_question = rewritten_question.replace(term, f"{term}({db_field})")
                    changes.append(f"术语映射：{term} -> {db_field}")
        
        # 4. 补充表名信息（如果上下文中有表名但问题中没有提到）
        if context and context.get("table_names") and len(context["table_names"]) == 1:
            table_name = context["table_names"][0]
            # 如果问题中没有提到表名，且只有一个表，可以隐式使用
            # 这里不修改问题，因为SQL生成时会自动使用
            pass
        
        # 5. 规范化SQL关键词
        sql_keywords = {
            'select': '查询',
            'where': '筛选条件',
            'group by': '分组',
            'order by': '排序',
            'limit': '限制数量'
        }
        
        # 6. 去除多余的空格和标点
        rewritten_question = re.sub(r'\s+', ' ', rewritten_question).strip()
        rewritten_question = re.sub(r'[，,]{2,}', '，', rewritten_question)
        
        # 如果问题没有变化，返回原问题
        if rewritten_question == original_question:
            return {
                "original_question": original_question,
                "rewritten_question": rewritten_question,
                "changes": [],
                "method": "rule",
                "warnings": warnings
            }
        
        return {
            "original_question": original_question,
            "rewritten_question": rewritten_question,
            "changes": changes,
            "method": "rule",
            "warnings": warnings
        }
    
    async def rewrite_question_async(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步版本的问题改写（支持LLM）
        
        Args:
            question: 原始问题
            context: 上下文信息
            
        Returns:
            改写结果
        """
        if not question or not question.strip():
            return {
                "original_question": question,
                "rewritten_question": question,
                "changes": [],
                "method": "none",
                "warnings": []
            }
        
        # 检测警告（与同步版本相同的逻辑）
        warnings = []
        
        # 检测是否涉及查询所有数据明细
        query_all_patterns = [
            r'查询.*所有.*数据',
            r'查看.*所有.*记录',
            r'显示.*全部.*信息',
            r'列出.*所有.*明细',
            r'所有.*数据.*明细',
            r'全部.*数据'
        ]
        
        for pattern in query_all_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                warnings.append("为了数据安全和性能考虑，系统不允许查询所有数据明细。建议使用统计查询（如COUNT、SUM等）或添加筛选条件。")
                break
        
        # 检测是否涉及修改数据操作
        modify_patterns = [
            r'删除|删除数据|删除记录',
            r'修改|更新|更改数据',
            r'插入|添加|新增数据',
            r'清空|清空数据|清空表'
        ]
        
        for pattern in modify_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                warnings.append("您没有权限执行修改数据的操作。系统只支持查询操作，请使用SELECT查询语句。")
                break
        
        # 优先使用LLM改写（如果可用）
        if self.llm_client:
            try:
                result = await self._rewrite_with_llm_async(question, context)
                # 确保返回结果包含warnings
                if "warnings" not in result:
                    result["warnings"] = warnings
                return result
            except Exception as e:
                logger.warning(f"LLM改写失败: {e}，降级到规则引擎")
        
        # 使用规则引擎改写（传递warnings）
        return self._rewrite_with_rules(question, context, warnings)
    
    async def _rewrite_with_llm_async(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用LLM异步改写问题
        
        Args:
            question: 原始问题
            context: 上下文信息
            
        Returns:
            改写结果
        """
        # 构建提示词
        prompt = f"""请优化以下用户问题，使其更清晰、具体，便于生成准确的SQL查询。

原始问题：{question}

"""
        
        if context:
            if context.get("table_names"):
                prompt += f"可用表名：{', '.join(context['table_names'][:10])}\n"
            if context.get("db_type"):
                prompt += f"数据库类型：{context['db_type']}\n"
        
        prompt += """
优化要求：
1. 保持原意不变
2. 补充缺失的关键信息（如时间范围、筛选条件等）
3. 规范化术语和表述
4. 如果问题模糊，添加合理的假设说明
5. 确保问题可以直接用于SQL生成

只返回优化后的问题，不要包含其他解释："""
        
        # 调用LLM（异步）
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.chat_completion(
                messages,
                temperature=0.3,  # 较低温度，保持一致性
                max_tokens=200
            )
            
            # 解析响应
            if isinstance(response, dict):
                rewritten_question = response.get("content", "") or response.get("message", {}).get("content", "")
            else:
                rewritten_question = str(response)
            
            # 清理响应（移除可能的Markdown格式）
            rewritten_question = rewritten_question.strip()
            rewritten_question = re.sub(r'^```.*?\n', '', rewritten_question, flags=re.DOTALL)
            rewritten_question = re.sub(r'\n```.*?$', '', rewritten_question, flags=re.DOTALL)
            rewritten_question = rewritten_question.strip()
            
            if rewritten_question and rewritten_question != question:
                return {
                    "original_question": question,
                    "rewritten_question": rewritten_question,
                    "changes": ["使用LLM优化了问题表述"],
                    "method": "llm",
                    "warnings": []  # LLM改写不检测警告，警告在调用方检测
                }
        except Exception as e:
            logger.error(f"LLM改写失败: {e}", exc_info=True)
            raise
        
        # 如果LLM改写失败或没有变化，使用规则引擎
        # 注意：这里需要传递warnings，但异步方法中没有定义，所以传递空列表
        # 警告应该在调用方（rewrite_question_async）中检测
        return self._rewrite_with_rules(question, context, [])

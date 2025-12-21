"""
探查结果知识库导入器
将探查结果导入到业务知识库，用于RAG增强
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.models import (
    ProbeTask, ProbeDatabaseResult, ProbeTableResult, 
    ProbeColumnResult, BusinessKnowledge
)


class ProbeResultKnowledgeImporter:
    """探查结果知识库导入器"""
    
    def __init__(self, db: Session):
        """
        初始化导入器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def import_to_knowledge(self, task_id: int, user_id: int) -> Dict[str, Any]:
        """
        导入探查结果到知识库
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            导入结果统计
        """
        task = self.db.query(ProbeTask).filter(ProbeTask.id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        imported_count = 0
        
        # 导入库级结果
        db_result = self.db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task_id
        ).first()
        
        if db_result:
            knowledge = self._format_database_knowledge(db_result, task)
            if knowledge:
                kb = BusinessKnowledge(
                    title=knowledge["title"],
                    content=knowledge["content"],
                    category="数据探查",
                    tags="数据源,库级探查",
                    created_by=user_id
                )
                self.db.add(kb)
                imported_count += 1
        
        # 导入表级结果
        table_results = self.db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id
        ).all()
        
        for tr in table_results:
            knowledge = self._format_table_knowledge(tr, task)
            if knowledge:
                kb = BusinessKnowledge(
                    title=knowledge["title"],
                    content=knowledge["content"],
                    category="数据探查",
                    tags="数据源,表级探查",
                    created_by=user_id
                )
                self.db.add(kb)
                imported_count += 1
        
        # 导入列级结果（重要字段）
        column_results = self.db.query(ProbeColumnResult).filter(
            ProbeColumnResult.task_id == task_id
        ).limit(100).all()  # 限制导入数量
        
        for cr in column_results:
            # 只导入有重要信息的字段（如主键、有注释、有敏感信息等）
            if (cr.comment or 
                (cr.sensitive_info and cr.sensitive_info.get("is_sensitive")) or
                cr.top_values):
                knowledge = self._format_column_knowledge(cr, task)
                if knowledge:
                    kb = BusinessKnowledge(
                        title=knowledge["title"],
                        content=knowledge["content"],
                        category="数据探查",
                        tags="数据源,列级探查",
                        created_by=user_id
                    )
                    self.db.add(kb)
                    imported_count += 1
        
        self.db.commit()
        
        logger.info(f"导入探查结果到知识库完成，任务ID: {task_id}，共导入 {imported_count} 条知识")
        
        return {
            "imported_count": imported_count,
            "task_id": task_id
        }
    
    def _format_database_knowledge(self, db_result: ProbeDatabaseResult, task: ProbeTask) -> Dict[str, Any]:
        """
        格式化库级探查结果为知识
        
        Args:
            db_result: 库级探查结果
            task: 探查任务
            
        Returns:
            格式化后的知识字典
        """
        content_parts = [
            f"数据库名称: {db_result.database_name}",
            f"数据库类型: {db_result.db_type}",
            f"表数量: {db_result.table_count}",
            f"视图数量: {db_result.view_count}",
        ]
        
        if db_result.total_size_mb:
            content_parts.append(f"总大小: {db_result.total_size_mb} MB")
        
        if db_result.top_n_tables:
            content_parts.append("\nTOP大表:")
            for table in db_result.top_n_tables[:5]:
                content_parts.append(f"  - {table.get('table_name', '')}: {table.get('size_mb', '')} MB")
        
        return {
            "title": f"{db_result.database_name} 数据库探查结果",
            "content": "\n".join(content_parts)
        }
    
    def _format_table_knowledge(self, table_result: ProbeTableResult, task: ProbeTask) -> Dict[str, Any]:
        """
        格式化表级探查结果为知识
        
        Args:
            table_result: 表级探查结果
            task: 探查任务
            
        Returns:
            格式化后的知识字典
        """
        content_parts = [
            f"表名: {table_result.table_name}",
            f"字段数: {table_result.column_count}",
        ]
        
        if table_result.row_count:
            content_parts.append(f"行数: {table_result.row_count}")
        
        if table_result.table_size_mb:
            content_parts.append(f"表大小: {table_result.table_size_mb} MB")
        
        if table_result.primary_key:
            pk_str = ", ".join(table_result.primary_key) if isinstance(table_result.primary_key, list) else str(table_result.primary_key)
            content_parts.append(f"主键: {pk_str}")
        
        if table_result.indexes:
            content_parts.append(f"索引数量: {len(table_result.indexes)}")
        
        return {
            "title": f"{table_result.table_name} 表结构信息",
            "content": "\n".join(content_parts)
        }
    
    def _format_column_knowledge(self, column_result: ProbeColumnResult, task: ProbeTask) -> Dict[str, Any]:
        """
        格式化列级探查结果为知识
        
        Args:
            column_result: 列级探查结果
            task: 探查任务
            
        Returns:
            格式化后的知识字典
        """
        content_parts = [
            f"表名: {column_result.table_name}",
            f"字段名: {column_result.column_name}",
            f"数据类型: {column_result.data_type}",
        ]
        
        if column_result.comment:
            content_parts.append(f"注释: {column_result.comment}")
        
        if column_result.non_null_rate:
            content_parts.append(f"非空率: {column_result.non_null_rate}")
        
        if column_result.distinct_count:
            content_parts.append(f"唯一值个数: {column_result.distinct_count}")
        
        if column_result.top_values:
            content_parts.append("\n高频值:")
            for value_info in column_result.top_values[:5]:
                content_parts.append(f"  - {value_info.get('value', '')}: {value_info.get('count', 0)}次")
        
        if column_result.sensitive_info and column_result.sensitive_info.get("is_sensitive"):
            sensitive_types = column_result.sensitive_info.get("sensitive_types", [])
            content_parts.append(f"\n敏感信息类型: {', '.join(sensitive_types)}")
        
        return {
            "title": f"{column_result.table_name}.{column_result.column_name} 字段信息",
            "content": "\n".join(content_parts)
        }


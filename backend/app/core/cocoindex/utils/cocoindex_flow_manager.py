"""
CocoIndex Flow 管理器
根据实际的 CocoIndex API 实现 Flow 的创建和管理
"""
from typing import Dict, Any, List, Optional, Iterator, Callable
from loguru import logger

try:
    from cocoindex import flow_def
    from cocoindex.flow import FlowBuilder, DataScope, Flow, flow_by_name
    from cocoindex.sources import Postgres as PostgresSource
    from cocoindex.targets import Postgres as PostgresTarget
    from cocoindex.index import VectorIndexDef, VectorSimilarityMetric
    from cocoindex.setting import DatabaseConnectionSpec
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False
    logger.warning("cocoindex 未安装，Flow 功能将不可用")


class CocoIndexFlowManager:
    """CocoIndex Flow 管理器"""
    
    def __init__(self):
        """初始化 Flow 管理器"""
        self.flows: Dict[str, Flow] = {}
        self.flow_definitions: Dict[str, Callable] = {}
    
    def create_flow(
        self,
        flow_name: str,
        source_table: str,
        target_table: str,
        source_db_config: Optional[DatabaseConnectionSpec] = None,
        target_db_config: Optional[DatabaseConnectionSpec] = None,
        primary_key_fields: Optional[List[str]] = None,
        vector_field: Optional[str] = None,
        vector_metric: Optional[VectorSimilarityMetric] = None
    ) -> Flow:
        """
        创建 CocoIndex Flow
        
        Args:
            flow_name: Flow 名称
            source_table: 源表名
            target_table: 目标表名
            source_db_config: 源数据库配置（可选）
            target_db_config: 目标数据库配置（可选）
            primary_key_fields: 主键字段列表
            vector_field: 向量字段名（可选）
            vector_metric: 向量相似度度量
            
        Returns:
            Flow 对象
        """
        if not COCOINDEX_AVAILABLE:
            raise ImportError("cocoindex 未安装，请安装 cocoindex")
        
        # 如果 Flow 已存在，直接返回
        if flow_name in self.flows:
            return self.flows[flow_name]
        
        # 创建 Flow 定义函数
        def flow_definition(builder: FlowBuilder, scope: DataScope):
            """Flow 定义函数"""
            # 添加 Source
            source_spec = PostgresSource(
                table_name=source_table,
                database=source_db_config
            )
            source = builder.add_source(source_spec, name="source")
            
            # 创建 DataCollector
            collector = builder.collect(source)
            
            # 准备导出参数
            export_kwargs = {
                "target_name": "target",
                "target_spec": PostgresTarget(
                    table_name=target_table,
                    database=target_db_config
                ),
                "primary_key_fields": primary_key_fields or ["id"]
            }
            
            # 如果有向量字段，添加向量索引
            if vector_field:
                # 使用默认的 COSINE_SIMILARITY 度量，如果未指定
                if vector_metric is None:
                    metric = VectorSimilarityMetric.COSINE_SIMILARITY
                else:
                    metric = vector_metric
                
                export_kwargs["vector_indexes"] = [
                    VectorIndexDef(
                        field_name=vector_field,
                        metric=metric
                    )
                ]
            
            # 导出到 Target
            collector.export(**export_kwargs)
            
            return builder
        
        # 使用 flow_def 装饰器创建 Flow
        flow_func = flow_def(name=flow_name)(flow_definition)
        
        # 获取 Flow 对象
        try:
            flow = flow_by_name(flow_name)
            self.flows[flow_name] = flow
            self.flow_definitions[flow_name] = flow_definition
            logger.info(f"Flow 创建成功: {flow_name}")
            return flow
        except Exception as e:
            logger.error(f"获取 Flow 失败: {e}")
            raise
    
    def setup_flow(self, flow_name: str) -> bool:
        """
        设置 Flow（创建表结构等）
        
        Args:
            flow_name: Flow 名称
            
        Returns:
            是否成功
        """
        try:
            flow = self.get_flow(flow_name)
            flow.setup(report_to_stdout=False)
            logger.info(f"Flow 设置成功: {flow_name}")
            return True
        except Exception as e:
            logger.error(f"Flow 设置失败: {e}", exc_info=True)
            return False
    
    def update_flow(
        self,
        flow_name: str,
        reexport_targets: bool = False,
        full_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        更新 Flow（同步数据）
        
        Args:
            flow_name: Flow 名称
            reexport_targets: 是否重新导出目标
            full_reprocess: 是否完全重新处理
            
        Returns:
            更新结果统计
        """
        try:
            flow = self.get_flow(flow_name)
            update_info = flow.update(
                reexport_targets=reexport_targets,
                full_reprocess=full_reprocess
            )
            
            logger.info(f"Flow 更新成功: {flow_name}")
            
            # 转换更新信息为字典
            return {
                "success": True,
                "flow_name": flow_name,
                "update_info": {
                    "rows_processed": getattr(update_info, "rows_processed", 0),
                    "rows_added": getattr(update_info, "rows_added", 0),
                    "rows_updated": getattr(update_info, "rows_updated", 0),
                    "rows_deleted": getattr(update_info, "rows_deleted", 0),
                }
            }
        except Exception as e:
            logger.error(f"Flow 更新失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_flow(self, flow_name: str) -> Flow:
        """
        获取 Flow 对象
        
        Args:
            flow_name: Flow 名称
            
        Returns:
            Flow 对象
        """
        if flow_name in self.flows:
            return self.flows[flow_name]
        
        try:
            flow = flow_by_name(flow_name)
            self.flows[flow_name] = flow
            return flow
        except Exception as e:
            logger.error(f"获取 Flow 失败: {e}")
            raise ValueError(f"Flow '{flow_name}' 不存在")
    
    def add_query_handler(
        self,
        flow_name: str,
        handler_name: str,
        handler: Callable[[str], Any]
    ) -> bool:
        """
        添加查询处理器
        
        Args:
            flow_name: Flow 名称
            handler_name: 处理器名称
            handler: 处理函数
            
        Returns:
            是否成功
        """
        try:
            flow = self.get_flow(flow_name)
            flow.add_query_handler(handler_name, handler)
            logger.info(f"查询处理器添加成功: {flow_name}.{handler_name}")
            return True
        except Exception as e:
            logger.error(f"添加查询处理器失败: {e}", exc_info=True)
            return False
    
    def drop_flow(self, flow_name: str) -> bool:
        """
        删除 Flow
        
        Args:
            flow_name: Flow 名称
            
        Returns:
            是否成功
        """
        try:
            flow = self.get_flow(flow_name)
            flow.drop(report_to_stdout=False)
            if flow_name in self.flows:
                del self.flows[flow_name]
            logger.info(f"Flow 删除成功: {flow_name}")
            return True
        except Exception as e:
            logger.error(f"删除 Flow 失败: {e}", exc_info=True)
            return False


# 全局 Flow 管理器实例
flow_manager = CocoIndexFlowManager()


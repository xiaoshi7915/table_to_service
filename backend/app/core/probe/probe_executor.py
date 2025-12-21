"""
探查任务执行器
负责执行探查任务，管理进度和结果保存
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from loguru import logger
from datetime import datetime

from app.models import ProbeTask, ProbeDatabaseResult, ProbeTableResult, ProbeColumnResult, DatabaseConfig
from .base_probe_engine import BaseProbeEngine
from .basic_probe_engine import BasicProbeEngine
from .advanced_probe_engine import AdvancedProbeEngine


class ProbeExecutor:
    """探查任务执行器"""
    
    def __init__(self, db: Session):
        """
        初始化执行器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """
        执行探查任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            执行结果
        """
        task = self.db.query(ProbeTask).filter(ProbeTask.id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 更新任务状态
        task.status = "running"
        task.start_time = datetime.now()
        task.progress = 0
        self.db.commit()
        
        try:
            # 获取数据库配置
            db_config = self.db.query(DatabaseConfig).filter(DatabaseConfig.id == task.database_config_id).first()
            if not db_config:
                raise ValueError(f"数据库配置不存在: {task.database_config_id}")
            
            # 根据探查方式选择引擎
            if task.probe_mode == "basic":
                engine = BasicProbeEngine(db_config)
            else:
                engine = AdvancedProbeEngine(db_config)
            
            engine.connect()
            
            try:
                # #region agent log
                import json, time
                with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"location":"probe_executor.py:64","message":"executing probe task","data":{"task_id":task.id,"probe_mode":task.probe_mode,"probe_level":task.probe_level,"engine_type":type(engine).__name__},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
                # #endregion
                
                # 根据探查级别执行不同的探查
                if task.probe_level == "database":
                    self._execute_database_probe(task, engine)
                elif task.probe_level == "table":
                    self._execute_table_probe(task, engine)
                elif task.probe_level == "column":
                    self._execute_column_probe(task, engine)
                else:
                    # 执行所有级别的探查
                    self._execute_database_probe(task, engine)
                    task.progress = 33
                    self.db.commit()
                    
                    self._execute_table_probe(task, engine)
                    task.progress = 66
                    self.db.commit()
                    
                    self._execute_column_probe(task, engine)
                    task.progress = 100
                    self.db.commit()
                
                # 更新任务状态
                task.status = "completed"
                task.end_time = datetime.now()
                task.last_probe_time = datetime.now()
                task.progress = 100
                self.db.commit()
                
                return {"success": True, "message": "探查任务执行成功"}
            
            finally:
                engine.disconnect()
        
        except Exception as e:
            logger.error(f"执行探查任务失败: {e}", exc_info=True)
            task.status = "failed"
            task.end_time = datetime.now()
            task.error_message = str(e)
            self.db.commit()
            raise
    
    def _execute_database_probe(self, task: ProbeTask, engine: BaseProbeEngine):
        """
        执行库级探查
        
        Args:
            task: 探查任务
            engine: 探查引擎
        """
        logger.info(f"开始执行库级探查，任务ID: {task.id}")
        
        # 执行探查
        result = engine.probe_database()
        
        # 检查是否已存在结果，如果存在则更新，否则创建
        db_result = self.db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task.id
        ).first()
        
        if db_result:
            # 更新现有结果（高级探查不会覆盖基础探查的数据，只更新/补充）
            db_result.database_name = result.get("database_name", db_result.database_name)
            db_result.db_type = result.get("db_type", db_result.db_type)
            db_result.total_size_mb = result.get("total_size_mb") or db_result.total_size_mb
            db_result.growth_rate = result.get("growth_rate") or db_result.growth_rate
            db_result.table_count = result.get("table_count", db_result.table_count)
            db_result.view_count = result.get("view_count", db_result.view_count)
            db_result.function_count = result.get("function_count", db_result.function_count)
            db_result.procedure_count = result.get("procedure_count", db_result.procedure_count)
            db_result.trigger_count = result.get("trigger_count", db_result.trigger_count)
            db_result.event_count = result.get("event_count", db_result.event_count)
            db_result.sequence_count = result.get("sequence_count", db_result.sequence_count)
            # 只更新非空的高级探查数据
            if result.get("top_n_tables"):
                db_result.top_n_tables = result.get("top_n_tables")
            if result.get("cold_tables"):
                db_result.cold_tables = result.get("cold_tables")
            if result.get("hot_tables"):
                db_result.hot_tables = result.get("hot_tables")
            if result.get("high_risk_accounts"):
                db_result.high_risk_accounts = result.get("high_risk_accounts")
            if result.get("permission_summary"):
                db_result.permission_summary = result.get("permission_summary")
        else:
            # 创建新结果
            db_result = ProbeDatabaseResult(
                task_id=task.id,
                database_name=result.get("database_name", ""),
                db_type=result.get("db_type", ""),
                total_size_mb=result.get("total_size_mb"),
                growth_rate=result.get("growth_rate"),
                table_count=result.get("table_count", 0),
                view_count=result.get("view_count", 0),
                function_count=result.get("function_count", 0),
                procedure_count=result.get("procedure_count", 0),
                trigger_count=result.get("trigger_count", 0),
                event_count=result.get("event_count", 0),
                sequence_count=result.get("sequence_count", 0),
                top_n_tables=result.get("top_n_tables"),
                cold_tables=result.get("cold_tables"),
                hot_tables=result.get("hot_tables"),
                high_risk_accounts=result.get("high_risk_accounts"),
                permission_summary=result.get("permission_summary"),
            )
            self.db.add(db_result)
        
        self.db.commit()
        
        logger.info(f"库级探查完成，任务ID: {task.id}")
    
    def _execute_table_probe(self, task: ProbeTask, engine: BaseProbeEngine):
        """
        执行表级探查
        
        Args:
            task: 探查任务
            engine: 探查引擎
        """
        logger.info(f"开始执行表级探查，任务ID: {task.id}")
        
        db_config = self.db.query(DatabaseConfig).filter(DatabaseConfig.id == task.database_config_id).first()
        database_name = db_config.database
        
        # 获取表列表
        from app.core.db_factory import DatabaseConnectionFactory
        from app.core.sql_dialect import SQLDialectFactory
        
        db_engine = DatabaseConnectionFactory.create_engine(db_config)
        inspector = inspect(db_engine)
        
        try:
            if db_config.db_type == "postgresql":
                table_names = inspector.get_table_names(schema="public")
            else:
                table_names = inspector.get_table_names()
            
            total_tables = len(table_names)
            logger.info(f"找到 {total_tables} 个表")
            
            # 探查每个表
            for idx, table_name in enumerate(table_names):
                try:
                    schema_name = "public" if db_config.db_type == "postgresql" else None
                    # #region agent log
                    import json, time
                    with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"location":"probe_executor.py:207","message":"probing table","data":{"task_id":task.id,"table_name":table_name,"probe_mode":task.probe_mode,"engine_type":type(engine).__name__},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
                    # #endregion
                    result = engine.probe_table(table_name, schema_name)
                    # #region agent log
                    with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"location":"probe_executor.py:210","message":"table probe result","data":{"task_id":task.id,"table_name":table_name,"has_row_count":result.get("row_count") is not None,"has_table_size":result.get("table_size_mb") is not None,"column_count":result.get("column_count",0)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
                    # #endregion
                    
                    # 检查是否已存在该表的结果
                    existing_table_result = self.db.query(ProbeTableResult).filter(
                        ProbeTableResult.task_id == task.id,
                        ProbeTableResult.table_name == table_name
                    ).first()
                    
                    if existing_table_result:
                        # 更新现有结果（高级探查不会覆盖基础探查的数据）
                        existing_table_result.row_count = result.get("row_count") or existing_table_result.row_count
                        existing_table_result.table_size_mb = result.get("table_size_mb") or existing_table_result.table_size_mb
                        existing_table_result.index_size_mb = result.get("index_size_mb") or existing_table_result.index_size_mb
                        existing_table_result.avg_row_length = result.get("avg_row_length") or existing_table_result.avg_row_length
                        existing_table_result.fragmentation_rate = result.get("fragmentation_rate") or existing_table_result.fragmentation_rate
                        existing_table_result.column_count = result.get("column_count", existing_table_result.column_count)
                        # 更新表注释（如果存在）
                        if result.get("table_comment"):
                            existing_table_result.comment = result.get("table_comment")
                        # 只更新非空的高级探查数据
                        if result.get("primary_key"):
                            existing_table_result.primary_key = result.get("primary_key")
                        if result.get("indexes"):
                            existing_table_result.indexes = result.get("indexes")
                        if result.get("foreign_keys"):
                            existing_table_result.foreign_keys = result.get("foreign_keys")
                        if result.get("constraints"):
                            existing_table_result.constraints = result.get("constraints")
                        if result.get("partition_info"):
                            existing_table_result.partition_info = result.get("partition_info")
                        if result.get("auto_increment_usage"):
                            existing_table_result.auto_increment_usage = result.get("auto_increment_usage")
                        existing_table_result.is_cold_table = result.get("is_cold_table", existing_table_result.is_cold_table)
                        existing_table_result.is_hot_table = result.get("is_hot_table", existing_table_result.is_hot_table)
                    else:
                        # 创建新结果
                        table_result = ProbeTableResult(
                            task_id=task.id,
                            database_name=database_name,
                            table_name=table_name,
                            schema_name=schema_name,
                            row_count=result.get("row_count"),
                            table_size_mb=result.get("table_size_mb"),
                            index_size_mb=result.get("index_size_mb"),
                            avg_row_length=result.get("avg_row_length"),
                            fragmentation_rate=result.get("fragmentation_rate"),
                            auto_increment_usage=result.get("auto_increment_usage"),
                            column_count=result.get("column_count", 0),
                            comment=result.get("table_comment"),
                            primary_key=result.get("primary_key"),
                            indexes=result.get("indexes"),
                            foreign_keys=result.get("foreign_keys"),
                            constraints=result.get("constraints"),
                            partition_info=result.get("partition_info"),
                            is_cold_table=result.get("is_cold_table", False),
                            is_hot_table=result.get("is_hot_table", False),
                        )
                        self.db.add(table_result)
                    
                    # 更新进度
                    progress = int((idx + 1) / total_tables * 100)
                    task.progress = min(progress, 99)  # 保留1%给最终完成
                    self.db.commit()
                    
                    # 每10个表提交一次
                    if (idx + 1) % 10 == 0:
                        self.db.commit()
                        logger.info(f"已探查 {idx + 1}/{total_tables} 个表")
                
                except Exception as e:
                    logger.error(f"探查表 {table_name} 失败: {e}", exc_info=True)
                    continue
            
            self.db.commit()
            logger.info(f"表级探查完成，任务ID: {task.id}")
        
        finally:
            db_engine.dispose()
    
    def _execute_column_probe(self, task: ProbeTask, engine: BaseProbeEngine):
        """
        执行列级探查
        
        Args:
            task: 探查任务
            engine: 探查引擎
        """
        logger.info(f"开始执行列级探查，任务ID: {task.id}")
        
        # 获取表结果列表（优先查找当前任务，如果没有则查找同一数据库配置的其他任务）
        table_results = self.db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task.id
        ).all()
        
        if not table_results:
            # 如果没有找到当前任务的表级结果，尝试查找同一数据库配置的其他任务的表级结果
            logger.warning(f"任务 {task.id} 没有找到表级探查结果，尝试查找同一数据库配置的其他任务的表级结果")
            other_tasks = self.db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed"
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                if other_task.id == task.id:
                    continue
                table_results = self.db.query(ProbeTableResult).filter(
                    ProbeTableResult.task_id == other_task.id
                ).all()
                if table_results:
                    logger.info(f"找到任务 {other_task.id} 的表级探查结果，共 {len(table_results)} 个表")
                    break
        
        if not table_results:
            logger.warning("没有找到表级探查结果，跳过列级探查")
            return
        
        db_config = self.db.query(DatabaseConfig).filter(DatabaseConfig.id == task.database_config_id).first()
        
        total_columns = 0
        processed_columns = 0
        
        # 探查每个表的每个字段
        for table_result in table_results:
            try:
                schema_name = table_result.schema_name
                
                # 获取表的字段列表
                from app.core.db_factory import DatabaseConnectionFactory
                from sqlalchemy import inspect as sql_inspect
                
                db_engine = DatabaseConnectionFactory.create_engine(db_config)
                inspector = sql_inspect(db_engine)
                
                try:
                    columns = inspector.get_columns(table_result.table_name, schema=schema_name)
                    total_columns += len(columns)
                    
                    for column in columns:
                        try:
                            column_name = column["name"]
                            # #region agent log
                            import json, time
                            with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                                f.write(json.dumps({"location":"probe_executor.py:329","message":"probing column","data":{"task_id":task.id,"table_name":table_result.table_name,"column_name":column_name,"probe_mode":task.probe_mode,"engine_type":type(engine).__name__},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
                            # #endregion
                            result = engine.probe_column(table_result.table_name, column_name, schema_name)
                            # #region agent log
                            with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                                f.write(json.dumps({"location":"probe_executor.py:332","message":"column probe result","data":{"task_id":task.id,"table_name":table_result.table_name,"column_name":column_name,"has_non_null_rate":result.get("non_null_rate") is not None,"has_distinct_count":result.get("distinct_count") is not None,"has_top_values":result.get("top_values") is not None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
                            # #endregion
                            
                            # 保存结果
                            column_result = ProbeColumnResult(
                                task_id=task.id,
                                table_result_id=table_result.id,
                                database_name=table_result.database_name,
                                table_name=table_result.table_name,
                                column_name=column_name,
                                data_type=result.get("data_type", ""),
                                nullable=result.get("nullable", True),
                                default_value=result.get("default_value"),
                                comment=result.get("comment"),
                                non_null_rate=result.get("non_null_rate"),
                                distinct_count=result.get("distinct_count"),
                                duplicate_rate=result.get("duplicate_rate"),
                                max_length=result.get("max_length"),
                                min_length=result.get("min_length"),
                                avg_length=result.get("avg_length"),
                                max_value=result.get("max_value"),
                                min_value=result.get("min_value"),
                                top_values=result.get("top_values"),
                                low_frequency_values=result.get("low_frequency_values"),
                                enum_values=result.get("enum_values"),
                                zero_count=result.get("zero_count"),
                                negative_count=result.get("negative_count"),
                                percentiles=result.get("percentiles"),
                                date_range=result.get("date_range"),
                                missing_rate=result.get("missing_rate"),
                                data_quality_issues=result.get("data_quality_issues"),
                                sensitive_info=result.get("sensitive_info"),
                            )
                            
                            self.db.add(column_result)
                            processed_columns += 1
                            
                            # 每50个字段提交一次
                            if processed_columns % 50 == 0:
                                self.db.commit()
                                logger.info(f"已探查 {processed_columns} 个字段")
                        
                        except Exception as e:
                            logger.error(f"探查字段 {table_result.table_name}.{column['name']} 失败: {e}", exc_info=True)
                            continue
                
                finally:
                    db_engine.dispose()
            
            except Exception as e:
                logger.error(f"处理表 {table_result.table_name} 的字段失败: {e}", exc_info=True)
                continue
        
        self.db.commit()
        logger.info(f"列级探查完成，任务ID: {task.id}，共探查 {processed_columns} 个字段")
    
    def stop_task(self, task_id: int):
        """
        停止探查任务
        
        Args:
            task_id: 任务ID
        """
        task = self.db.query(ProbeTask).filter(ProbeTask.id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status == "running":
            task.status = "stopped"
            task.end_time = datetime.now()
            self.db.commit()
            logger.info(f"任务已停止: {task_id}")


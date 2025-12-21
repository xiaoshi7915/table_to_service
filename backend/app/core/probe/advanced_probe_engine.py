"""
高级探查引擎
探查表结构和数据内容，包括数据分布、质量检测、敏感信息检测等
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import text, inspect
from loguru import logger
import json

from .basic_probe_engine import BasicProbeEngine
from .data_quality_checker import DataQualityChecker
from .sensitive_info_detector import SensitiveInfoDetector
from .database_adapters import (
    MySQLAdapter, PostgreSQLAdapter, SQLServerAdapter, 
    OracleAdapter, SQLiteAdapter
)


class AdvancedProbeEngine(BasicProbeEngine):
    """高级探查引擎 - 探查表结构和数据内容"""
    
    def probe_database(self) -> Dict[str, Any]:
        """
        库级探查（高级探查）
        包括容量画像、对象清单、权限与敏感账号
        
        Returns:
            库级探查结果字典
        """
        # 先执行基础探查
        result = super().probe_database()
        
        adapter = self._get_adapter()
        database_name = self.db_config.database
        
        try:
            with self.engine.connect() as conn:
                # 获取容量画像
                try:
                    if self.db_type == "postgresql":
                        capacity_query = adapter.get_database_capacity_query(database_name, schema_name="public")
                    else:
                        capacity_query = adapter.get_database_capacity_query(database_name)
                    
                    capacity_result = conn.execute(text(capacity_query)).fetchone()
                    if capacity_result:
                        if self.db_type == "postgresql":
                            result["total_size_mb"] = str(round(capacity_result[2] / 1024 / 1024, 2)) if len(capacity_result) > 2 else None
                        else:
                            result["total_size_mb"] = str(capacity_result[1]) if len(capacity_result) > 1 else None
                except Exception as e:
                    logger.warning(f"获取容量画像失败: {e}")
                
                # 获取TOP N大表
                try:
                    if self.db_type == "postgresql":
                        top_tables_query = adapter.get_top_n_tables_query(database_name, schema_name="public", n=10)
                    else:
                        top_tables_query = adapter.get_top_n_tables_query(database_name, n=10)
                    
                    top_tables_result = conn.execute(text(top_tables_query)).fetchall()
                    top_tables = []
                    for row in top_tables_result:
                        if self.db_type == "postgresql":
                            top_tables.append({
                                "table_name": row[0],
                                "size_mb": str(round(row[2] / 1024 / 1024, 2)) if len(row) > 2 else None
                            })
                        else:
                            top_tables.append({
                                "table_name": row[0],
                                "size_mb": str(row[1]) if len(row) > 1 else None
                            })
                    result["top_n_tables"] = top_tables
                except Exception as e:
                    logger.warning(f"获取TOP N大表失败: {e}")
        
        except Exception as e:
            logger.error(f"高级库级探查失败: {e}", exc_info=True)
        
        return result
    
    def probe_table(self, table_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        表级探查（高级探查）
        包括行级统计、冷热访问分析
        
        Args:
            table_name: 表名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            表级探查结果字典
        """
        # #region agent log
        import json, time
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:83","message":"advanced probe_table entry","data":{"table_name":table_name,"schema_name":schema_name},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        # #endregion
        # 先执行基础探查
        result = super().probe_table(table_name, schema_name)
        # #region agent log
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:97","message":"after basic probe_table","data":{"table_name":table_name,"has_row_count":result.get("row_count") is not None,"has_table_size":result.get("table_size_mb") is not None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        # #endregion
        
        adapter = self._get_adapter()
        database_name = self.db_config.database
        
        try:
            with self.engine.connect() as conn:
                # 获取表统计信息
                try:
                    if self.db_type == "postgresql":
                        table_info_query = adapter.get_table_info_query(database_name, table_name, schema_name="public")
                    else:
                        table_info_query = adapter.get_table_info_query(database_name, table_name)
                    
                    table_info_result = conn.execute(text(table_info_query)).fetchone()
                    if table_info_result:
                        if self.db_type == "postgresql":
                            result["row_count"] = int(table_info_result[5]) if len(table_info_result) > 5 else None
                            result["table_size_mb"] = str(round(table_info_result[3] / 1024 / 1024, 2)) if len(table_info_result) > 3 else None
                        else:
                            result["row_count"] = int(table_info_result[1]) if len(table_info_result) > 1 else None
                            result["table_size_mb"] = str(table_info_result[2]) if len(table_info_result) > 2 else None
                except Exception as e:
                    logger.warning(f"获取表统计信息失败: {e}")
                
                # 冷热表分析（简化版：基于表大小和行数判断）
                # 大表（>100MB）或行数多（>100万）的标记为热表
                # 小表（<1MB）且行数少（<1000）的标记为冷表
                try:
                    table_size_mb = float(result.get("table_size_mb", 0) or 0)
                    row_count = result.get("row_count", 0) or 0
                    
                    if table_size_mb > 100 or row_count > 1000000:
                        result["is_hot_table"] = True
                        result["is_cold_table"] = False
                    elif table_size_mb < 1 and row_count < 1000:
                        result["is_cold_table"] = True
                        result["is_hot_table"] = False
                    else:
                        result["is_cold_table"] = False
                        result["is_hot_table"] = False
                except Exception as e:
                    logger.warning(f"冷热表分析失败: {e}")
                    result["is_cold_table"] = False
                    result["is_hot_table"] = False
        
        except Exception as e:
            logger.error(f"高级表级探查失败: {e}", exc_info=True)
            # #region agent log
            import json, time, traceback
            with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"advanced_probe_engine.py:122","message":"advanced probe_table error","data":{"table_name":table_name,"error":str(e),"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
            # #endregion
        
        # #region agent log
        import json, time
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:124","message":"advanced probe_table return","data":{"table_name":table_name,"row_count":result.get("row_count"),"table_size_mb":result.get("table_size_mb"),"has_cold_hot":result.get("is_cold_table") is not None or result.get("is_hot_table") is not None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
        # #endregion
        return result
    
    def probe_column(
        self, 
        table_name: str, 
        column_name: str, 
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        列级探查（高级探查）
        包括基础分布、值域与枚举、数据质量规则、敏感与隐私检测
        
        Args:
            table_name: 表名
            column_name: 字段名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            列级探查结果字典
        """
        # #region agent log
        import json, time
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:126","message":"advanced probe_column entry","data":{"table_name":table_name,"column_name":column_name,"schema_name":schema_name},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
        # #endregion
        # 先执行基础探查
        result = super().probe_column(table_name, column_name, schema_name)
        # #region agent log
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:145","message":"after basic probe_column","data":{"table_name":table_name,"column_name":column_name,"data_type":result.get("data_type")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
        # #endregion
        
        adapter = self._get_adapter()
        database_name = self.db_config.database
        data_type = result.get("data_type", "")
        
        try:
            with self.engine.connect() as conn:
                # 获取字段统计信息
                try:
                    if self.db_type == "postgresql":
                        stats_query = adapter.get_column_statistics_query(database_name, table_name, column_name, schema_name="public")
                    else:
                        stats_query = adapter.get_column_statistics_query(database_name, table_name, column_name)
                    
                    stats_result = conn.execute(text(stats_query)).fetchone()
                    if stats_result:
                        total_cnt = stats_result[0] if len(stats_result) > 0 else 0
                        non_null_cnt = stats_result[1] if len(stats_result) > 1 else 0
                        distinct_cnt = stats_result[2] if len(stats_result) > 2 else 0
                        
                        result["non_null_rate"] = f"{non_null_cnt / total_cnt * 100:.2f}%" if total_cnt > 0 else "0%"
                        result["distinct_count"] = distinct_cnt
                        result["duplicate_rate"] = f"{(total_cnt - distinct_cnt) / total_cnt * 100:.2f}%" if total_cnt > 0 else "0%"
                except Exception as e:
                    logger.warning(f"获取字段统计信息失败: {e}")
                
                # 获取值域信息（数值/日期类型）
                try:
                    if self.db_type == "postgresql":
                        range_query = adapter.get_column_value_range_query(database_name, table_name, column_name, data_type, schema_name="public")
                    else:
                        range_query = adapter.get_column_value_range_query(database_name, table_name, column_name, data_type)
                    
                    range_result = conn.execute(text(range_query)).fetchone()
                    if range_result:
                        if 'int' in data_type.lower() or 'numeric' in data_type.lower() or 'decimal' in data_type.lower() or 'float' in data_type.lower():
                            result["max_value"] = str(range_result[0]) if len(range_result) > 0 and range_result[0] is not None else None
                            result["min_value"] = str(range_result[1]) if len(range_result) > 1 and range_result[1] is not None else None
                            result["zero_count"] = int(range_result[3]) if len(range_result) > 3 and range_result[3] is not None else None
                            result["negative_count"] = int(range_result[4]) if len(range_result) > 4 and range_result[4] is not None else None
                        elif 'varchar' in data_type.lower() or 'char' in data_type.lower() or 'text' in data_type.lower():
                            result["max_length"] = int(range_result[0]) if len(range_result) > 0 and range_result[0] is not None else None
                            result["min_length"] = int(range_result[1]) if len(range_result) > 1 and range_result[1] is not None else None
                            result["avg_length"] = f"{range_result[2]:.2f}" if len(range_result) > 2 and range_result[2] is not None else None
                        elif 'date' in data_type.lower() or 'time' in data_type.lower():
                            result["max_value"] = str(range_result[0]) if len(range_result) > 0 and range_result[0] is not None else None
                            result["min_value"] = str(range_result[1]) if len(range_result) > 1 and range_result[1] is not None else None
                except Exception as e:
                    logger.warning(f"获取值域信息失败: {e}")
                
                # 获取Top N高频值
                try:
                    sample_limit = 10000  # 采样限制，避免大表查询过慢
                    if self.db_type == "postgresql":
                        top_values_query = adapter.get_top_values_query(database_name, table_name, column_name, schema_name="public", limit=20)
                        # 对于PostgreSQL，使用子查询添加采样限制
                        if f"FROM {schema_name or 'public'}.{table_name}" in top_values_query:
                            top_values_query = top_values_query.replace(
                                f"FROM {schema_name or 'public'}.{table_name}",
                                f"FROM (SELECT * FROM {schema_name or 'public'}.{table_name} LIMIT {sample_limit}) AS sampled"
                            )
                    else:
                        top_values_query = adapter.get_top_values_query(database_name, table_name, column_name, limit=20)
                        # 对于MySQL，使用子查询添加采样限制
                        if f"FROM `{database_name}`.`{table_name}`" in top_values_query:
                            top_values_query = top_values_query.replace(
                                f"FROM `{database_name}`.`{table_name}`",
                                f"FROM (SELECT * FROM `{database_name}`.`{table_name}` LIMIT {sample_limit}) AS sampled"
                            )
                        elif f"FROM [{database_name}].[dbo].[{table_name}]" in top_values_query:
                            # SQL Server
                            top_values_query = top_values_query.replace(
                                f"FROM [{database_name}].[dbo].[{table_name}]",
                                f"FROM (SELECT TOP {sample_limit} * FROM [{database_name}].[dbo].[{table_name}]) AS sampled"
                            )
                    
                    top_values_result = conn.execute(text(top_values_query)).fetchall()
                    top_values = []
                    for row in top_values_result:
                        top_values.append({
                            "value": str(row[0]) if len(row) > 0 else None,
                            "count": int(row[1]) if len(row) > 1 else 0
                        })
                    result["top_values"] = top_values
                    
                    # 使用样本值进行敏感信息检测
                    sample_values = [row[0] for row in top_values_result[:10]]  # 取前10个样本
                    sensitive_detection = SensitiveInfoDetector.detect_in_column(column_name, sample_values)
                    result["sensitive_info"] = sensitive_detection
                    
                    # 数据质量检测
                    quality_issues = DataQualityChecker.detect_format_issues(sample_values, column_name)
                    result["data_quality_issues"] = quality_issues
                    
                except Exception as e:
                    logger.warning(f"获取Top值或检测敏感信息失败: {e}")
        
        except Exception as e:
            logger.error(f"高级列级探查失败: {e}", exc_info=True)
            # #region agent log
            import json, time, traceback
            with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"advanced_probe_engine.py:272","message":"advanced probe_column error","data":{"table_name":table_name,"column_name":column_name,"error":str(e),"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
            # #endregion
        
        # #region agent log
        import json, time
        with open('/opt/table_to_service/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"advanced_probe_engine.py:274","message":"advanced probe_column return","data":{"table_name":table_name,"column_name":column_name,"has_non_null_rate":result.get("non_null_rate") is not None,"has_distinct_count":result.get("distinct_count") is not None,"has_top_values":result.get("top_values") is not None,"top_values_count":len(result.get("top_values",[])) if result.get("top_values") else 0},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
        # #endregion
        return result


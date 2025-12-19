"""
图表生成服务
根据问题意图和数据特征生成图表配置
"""
from typing import Dict, Any, List, Optional
from loguru import logger
import re


class ChartService:
    """图表生成服务"""
    
    def __init__(self):
        """初始化图表服务"""
        pass
    
    def generate_chart_config(
        self,
        question: str,
        data: List[Dict[str, Any]],
        sql: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            question: 用户问题
            data: 查询结果数据
            sql: SQL语句（可选，用于辅助判断）
            
        Returns:
            图表配置字典（ECharts格式）
        """
        if not data:
            return {
                "type": "table",
                "message": "查询结果为空"
            }
        
        # 分析问题和数据特征
        question_lower = question.lower()
        columns = list(data[0].keys())
        row_count = len(data)
        
        # 1. 根据问题关键词推荐图表类型
        chart_type = self._recommend_chart_type(question_lower, columns, sql)
        
        # 2. 预处理数据
        processed_data = self._preprocess_data(data, chart_type)
        
        # 3. 生成图表配置
        chart_config = self._build_chart_config(
            chart_type,
            processed_data,
            columns,
            question
        )
        
        return chart_config
    
    def _recommend_chart_type(
        self,
        question: str,
        columns: List[str],
        sql: Optional[str] = None
    ) -> str:
        """
        推荐图表类型
        
        Args:
            question: 用户问题（小写）
            columns: 数据列名
            sql: SQL语句
            
        Returns:
            图表类型（bar, line, pie, table, scatter, area）
        """
        # 关键词匹配
        if any(kw in question for kw in ["趋势", "变化", "增长", "下降", "时间", "趋势", "走势"]):
            return "line"
        
        if any(kw in question for kw in ["占比", "比例", "百分比", "分布", "构成"]):
            return "pie"
        
        if any(kw in question for kw in ["排名", "最高", "最低", "前", "top", "最大", "最小"]):
            return "bar"
        
        if any(kw in question for kw in ["关系", "相关性", "散点"]):
            return "scatter"
        
        # 根据数据特征判断
        if len(columns) >= 2:
            # 检查是否有数值列
            numeric_columns = self._detect_numeric_columns(columns)
            if len(numeric_columns) >= 2:
                return "scatter"
        
        # 根据SQL判断
        if sql:
            sql_upper = sql.upper()
            if "GROUP BY" in sql_upper and "COUNT" in sql_upper:
                # 分组统计，适合柱状图或饼图
                if "ORDER BY" in sql_upper:
                    return "bar"
                return "pie"
            elif "SUM" in sql_upper or "AVG" in sql_upper:
                # 聚合查询，适合柱状图
                return "bar"
        
        # 默认：表格
        return "table"
    
    def _detect_numeric_columns(self, columns: List[str]) -> List[str]:
        """
        检测数值列（基于列名）
        
        Args:
            columns: 列名列表
            
        Returns:
            数值列名列表
        """
        numeric_keywords = [
            "count", "sum", "avg", "max", "min", "total", "amount",
            "price", "salary", "quantity", "number", "num", "数量",
            "金额", "价格", "总计", "总和", "平均"
        ]
        
        numeric_columns = []
        for col in columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in numeric_keywords):
                numeric_columns.append(col)
        
        return numeric_columns
    
    def _preprocess_data(
        self,
        data: List[Dict[str, Any]],
        chart_type: str
    ) -> List[Dict[str, Any]]:
        """
        预处理数据
        
        Args:
            data: 原始数据
            chart_type: 图表类型
            
        Returns:
            预处理后的数据
        """
        if not data:
            return []
        
        processed = []
        
        for row in data:
            processed_row = {}
            for key, value in row.items():
                # 格式化数值
                if isinstance(value, (int, float)):
                    processed_row[key] = value
                elif isinstance(value, str):
                    # 尝试转换为数值
                    try:
                        if '.' in value:
                            processed_row[key] = float(value)
                        else:
                            processed_row[key] = int(value)
                    except:
                        processed_row[key] = value
                else:
                    processed_row[key] = value
            
            processed.append(processed_row)
        
        # 根据图表类型排序
        if chart_type in ["bar", "line"]:
            # 按第一个数值列降序排序
            numeric_cols = self._detect_numeric_columns(list(processed[0].keys()))
            if numeric_cols:
                processed.sort(
                    key=lambda x: x.get(numeric_cols[0], 0),
                    reverse=True
                )
        
        return processed
    
    def _build_chart_config(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        columns: List[str],
        question: str
    ) -> Dict[str, Any]:
        """
        构建图表配置
        
        Args:
            chart_type: 图表类型
            data: 预处理后的数据
            columns: 列名列表
            question: 用户问题
            
        Returns:
            ECharts配置字典
        """
        if chart_type == "table":
            return {
                "type": "table",
                "columns": columns,
                "data": data[:100]  # 表格最多显示100条
            }
        
        # 提取X轴和Y轴数据
        x_column = columns[0] if columns else None
        y_columns = columns[1:] if len(columns) > 1 else columns
        
        # 限制数据量（图表最多显示50条）
        chart_data = data[:50]
        
        if chart_type == "bar":
            return {
                "type": "bar",
                "title": question,
                "xAxis": {
                    "type": "category",
                    "data": [str(row.get(x_column, "")) for row in chart_data]
                },
                "yAxis": {
                    "type": "value"
                },
                "series": [
                    {
                        "name": col,
                        "type": "bar",
                        "data": [row.get(col, 0) for row in chart_data]
                    }
                    for col in y_columns[:3]  # 最多3个系列
                ]
            }
        
        elif chart_type == "line":
            return {
                "type": "line",
                "title": question,
                "xAxis": {
                    "type": "category",
                    "data": [str(row.get(x_column, "")) for row in chart_data]
                },
                "yAxis": {
                    "type": "value"
                },
                "series": [
                    {
                        "name": col,
                        "type": "line",
                        "data": [row.get(col, 0) for row in chart_data]
                    }
                    for col in y_columns[:3]  # 最多3个系列
                ]
            }
        
        elif chart_type == "pie":
            # 饼图需要：名称和数值
            if len(columns) >= 2:
                name_col = columns[0]
                value_col = columns[1]
            else:
                name_col = columns[0] if columns else "name"
                value_col = None
            
            pie_data = []
            for row in chart_data[:20]:  # 饼图最多20项
                name = str(row.get(name_col, ""))
                value = row.get(value_col, 0) if value_col else 1
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except:
                        value = 1
                pie_data.append({"name": name, "value": value})
            
            return {
                "type": "pie",
                "title": question,
                "series": [{
                    "type": "pie",
                    "data": pie_data,
                    "radius": "60%"
                }]
            }
        
        elif chart_type == "scatter":
            if len(columns) >= 2:
                x_col = columns[0]
                y_col = columns[1]
            else:
                x_col = columns[0] if columns else "x"
                y_col = columns[0] if columns else "y"
            
            scatter_data = [
                [row.get(x_col, 0), row.get(y_col, 0)]
                for row in chart_data[:100]  # 散点图最多100个点
            ]
            
            return {
                "type": "scatter",
                "title": question,
                "xAxis": {"type": "value"},
                "yAxis": {"type": "value"},
                "series": [{
                    "type": "scatter",
                    "data": scatter_data
                }]
            }
        
        elif chart_type == "area":
            return {
                "type": "line",
                "title": question,
                "xAxis": {
                    "type": "category",
                    "data": [str(row.get(x_column, "")) for row in chart_data]
                },
                "yAxis": {
                    "type": "value"
                },
                "series": [
                    {
                        "name": col,
                        "type": "line",
                        "areaStyle": {},
                        "data": [row.get(col, 0) for row in chart_data]
                    }
                    for col in y_columns[:3]
                ]
            }
        
        # 默认返回表格
        return {
            "type": "table",
            "columns": columns,
            "data": data[:100]
        }
    
    def convert_chart_type(
        self,
        chart_config: Dict[str, Any],
        target_type: str
    ) -> Dict[str, Any]:
        """
        转换图表类型
        
        Args:
            chart_config: 当前图表配置
            target_type: 目标图表类型
            
        Returns:
            转换后的图表配置
        """
        if chart_config.get("type") == target_type:
            return chart_config
        
        # 提取数据
        data = chart_config.get("data", [])
        columns = chart_config.get("columns", [])
        question = chart_config.get("title", "")
        
        # 重新生成配置
        return self._build_chart_config(target_type, data, columns, question)


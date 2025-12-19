"""
数据导出API
支持Excel、CSV、PNG格式导出
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger
import io
import json
import csv
from datetime import datetime

from app.core.database import get_local_db
from app.models import User, ChatMessage
from app.schemas import ResponseModel
from app.core.security import get_current_active_user

router = APIRouter(prefix="/api/v1/chat", tags=["对话导出"])


@router.get("/messages/{message_id}/export")
async def export_message_data(
    message_id: int,
    format: str = Query("excel", regex="^(excel|csv|png)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """
    导出消息数据
    
    Args:
        message_id: 消息ID
        format: 导出格式（excel, csv, png）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        导出文件流
    """
    try:
        # 1. 验证消息和用户权限
        from app.models import ChatSession
        message = db.query(ChatMessage).filter(
            ChatMessage.id == message_id
        ).first()
        
        if not message:
            raise HTTPException(status_code=404, detail="消息不存在")
        
        # 验证用户权限（通过会话）
        session = db.query(ChatSession).filter(
            ChatSession.id == message.session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=403, detail="无权访问此消息")
        
        # 2. 解析数据
        data = []
        if message.query_result:
            try:
                data = json.loads(message.query_result)
            except:
                data = []
        
        chart_config = None
        if message.chart_config:
            try:
                chart_config = json.loads(message.chart_config)
            except:
                chart_config = None
        
        # 3. 根据格式导出
        if format == "excel":
            return export_to_excel(data, message)
        elif format == "csv":
            return export_to_csv(data, message)
        elif format == "png":
            if not chart_config:
                raise HTTPException(status_code=400, detail="该消息没有图表数据")
            return export_chart_to_png(chart_config, message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")


def export_to_excel(data: list, message: ChatMessage):
    """
    导出为Excel格式
    
    Args:
        data: 数据列表
        message: 消息对象
        
    Returns:
        Excel文件流
    """
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        
        # 创建DataFrame
        if not data:
            df = pd.DataFrame({"提示": ["该消息没有数据"]})
        else:
            df = pd.DataFrame(data)
        
        # 创建Excel工作簿
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='数据', index=False)
            
            # 获取工作表
            worksheet = writer.sheets['数据']
            
            # 设置标题样式
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # 自动调整列宽
            for column in worksheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        filename = f"数据导出_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ImportError:
        # 如果没有pandas/openpyxl，使用xlsxwriter
        try:
            import xlsxwriter
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('数据')
            
            # 设置标题样式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': '#FFFFFF',
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # 写入数据
            if data:
                # 写入表头
                columns = list(data[0].keys())
                for col_idx, col_name in enumerate(columns):
                    worksheet.write(0, col_idx, col_name, header_format)
                
                # 写入数据
                for row_idx, row_data in enumerate(data, 1):
                    for col_idx, col_name in enumerate(columns):
                        value = row_data.get(col_name, '')
                        worksheet.write(row_idx, col_idx, value)
                
                # 自动调整列宽
                for col_idx, col_name in enumerate(columns):
                    worksheet.set_column(col_idx, col_idx, min(len(str(col_name)) + 2, 50))
            else:
                worksheet.write(0, 0, "该消息没有数据", header_format)
            
            workbook.close()
            output.seek(0)
            
            filename = f"数据导出_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="Excel导出功能需要安装pandas或xlsxwriter库")
    except Exception as e:
        logger.error(f"Excel导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel导出失败: {str(e)}")


def export_to_csv(data: list, message: ChatMessage):
    """
    导出为CSV格式
    
    Args:
        data: 数据列表
        message: 消息对象
        
    Returns:
        CSV文件流
    """
    try:
        output = io.StringIO()
        
        if not data:
            writer = csv.writer(output)
            writer.writerow(["提示"])
            writer.writerow(["该消息没有数据"])
        else:
            # 获取列名
            columns = list(data[0].keys())
            
            # 写入CSV
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        
        output.seek(0)
        csv_bytes = output.getvalue().encode('utf-8-sig')  # 使用UTF-8 BOM以支持Excel正确显示中文
        
        filename = f"数据导出_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8-sig"
            }
        )
        
    except Exception as e:
        logger.error(f"CSV导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CSV导出失败: {str(e)}")


def export_chart_to_png(chart_config: dict, message: ChatMessage):
    """
    导出图表为PNG格式
    
    Args:
        chart_config: 图表配置
        message: 消息对象
        
    Returns:
        PNG图片流
    """
    try:
        # 使用matplotlib或PIL生成图片
        # 这里简化实现，实际应该使用ECharts的图片导出功能或matplotlib
        
        # 方案1: 如果有数据，使用matplotlib生成
        try:
            import matplotlib
            matplotlib.use('Agg')  # 使用非交互式后端
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            chart_type = chart_config.get("type", "bar")
            
            if chart_type == "bar":
                # 柱状图
                x_data = chart_config.get("xAxis", {}).get("data", [])
                series = chart_config.get("series", [])
                
                if series and len(series) > 0:
                    y_data = series[0].get("data", [])
                    
                    plt.figure(figsize=(10, 6))
                    plt.bar(range(len(x_data)), y_data)
                    plt.xticks(range(len(x_data)), x_data, rotation=45, ha='right')
                    plt.title(chart_config.get("title", "图表"))
                    plt.tight_layout()
                    
                    output = io.BytesIO()
                    plt.savefig(output, format='png', dpi=150, bbox_inches='tight')
                    plt.close()
                    output.seek(0)
                    
                    filename = f"图表_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    
                    return Response(
                        content=output.read(),
                        media_type="image/png",
                        headers={"Content-Disposition": f"attachment; filename={filename}"}
                    )
            
            elif chart_type == "line":
                # 折线图
                x_data = chart_config.get("xAxis", {}).get("data", [])
                series = chart_config.get("series", [])
                
                if series and len(series) > 0:
                    plt.figure(figsize=(10, 6))
                    for s in series:
                        y_data = s.get("data", [])
                        plt.plot(range(len(x_data)), y_data, marker='o', label=s.get("name", "系列"))
                    plt.xticks(range(len(x_data)), x_data, rotation=45, ha='right')
                    plt.title(chart_config.get("title", "图表"))
                    plt.legend()
                    plt.tight_layout()
                    
                    output = io.BytesIO()
                    plt.savefig(output, format='png', dpi=150, bbox_inches='tight')
                    plt.close()
                    output.seek(0)
                    
                    filename = f"图表_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    
                    return Response(
                        content=output.read(),
                        media_type="image/png",
                        headers={"Content-Disposition": f"attachment; filename={filename}"}
                    )
            
            elif chart_type == "pie":
                # 饼图
                series = chart_config.get("series", [])
                
                if series and len(series) > 0:
                    pie_data = series[0].get("data", [])
                    
                    labels = [item.get("name", "") for item in pie_data]
                    values = [item.get("value", 0) for item in pie_data]
                    
                    plt.figure(figsize=(8, 8))
                    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
                    plt.title(chart_config.get("title", "图表"))
                    plt.axis('equal')
                    
                    output = io.BytesIO()
                    plt.savefig(output, format='png', dpi=150, bbox_inches='tight')
                    plt.close()
                    output.seek(0)
                    
                    filename = f"图表_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    
                    return Response(
                        content=output.read(),
                        media_type="image/png",
                        headers={"Content-Disposition": f"attachment; filename={filename}"}
                    )
            
            raise HTTPException(status_code=400, detail=f"不支持的图表类型: {chart_type}")
            
        except ImportError:
            raise HTTPException(status_code=500, detail="PNG导出功能需要安装matplotlib库")
        
    except Exception as e:
        logger.error(f"PNG导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PNG导出失败: {str(e)}")


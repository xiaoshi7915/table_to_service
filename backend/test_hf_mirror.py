#!/usr/bin/env python3
"""
测试 Hugging Face 镜像源配置
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_file = Path('/opt/table_to_service/.env')
if env_file.exists():
    load_dotenv(env_file)
    print('✅ .env 文件加载成功')
else:
    print('❌ .env 文件不存在')

# 设置环境变量（如果未设置）
if not os.getenv('HF_ENDPOINT'):
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    print('✅ 设置默认镜像源: https://hf-mirror.com')

print(f'\n当前配置:')
print(f'  HF_ENDPOINT: {os.getenv("HF_ENDPOINT")}')
print(f'  HF_HUB_CACHE: {os.getenv("HF_HUB_CACHE", "未设置")}')

# 测试导入
print('\n测试导入...')
try:
    from app.core.rag_langchain.embedding_service import ChineseEmbeddingService
    print('✅ ChineseEmbeddingService 导入成功')
except Exception as e:
    print(f'❌ 导入失败: {e}')
    sys.exit(1)

# 测试初始化（这会尝试下载模型）
print('\n测试模型初始化（首次运行会下载模型，可能需要几分钟）...')
try:
    service = ChineseEmbeddingService()
    print('✅ ChineseEmbeddingService 初始化成功')
    
    # 测试生成嵌入向量
    print('\n测试生成嵌入向量...')
    result = service.embed_query('测试文本')
    print(f'✅ 嵌入向量生成成功，维度: {len(result)}')
    print(f'   前5个值: {result[:5]}')
    
except Exception as e:
    print(f'\n⚠️  模型初始化或下载失败: {e}')
    print('\n可能的原因:')
    print('  1. 网络连接问题（无法访问镜像源）')
    print('  2. 镜像源配置错误')
    print('  3. 模型文件下载不完整')
    print('\n解决方案:')
    print('  1. 检查网络连接')
    print('  2. 确认 .env 文件中的 HF_ENDPOINT 配置正确')
    print('  3. 尝试手动下载模型到缓存目录')
    sys.exit(1)

print('\n✅ 所有测试通过！')

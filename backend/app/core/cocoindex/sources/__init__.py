"""
CocoIndex 数据源模块
支持多种数据源的适配器
"""
from .base_source import BaseSource
from .postgresql_source import PostgreSQLSource
from .mysql_source import MySQLSource
from .file_source import FileSource
from .database_schema_source import DatabaseSchemaSource
from .mongodb_source import MongoDBSource
from .s3_source import S3Source
from .azure_blob_source import AzureBlobSource
from .google_drive_source import GoogleDriveSource
from .api_source import APISource

__all__ = [
    "BaseSource",
    "PostgreSQLSource",
    "MySQLSource",
    "FileSource",
    "DatabaseSchemaSource",
    "MongoDBSource",
    "S3Source",
    "AzureBlobSource",
    "GoogleDriveSource",
    "APISource",
]


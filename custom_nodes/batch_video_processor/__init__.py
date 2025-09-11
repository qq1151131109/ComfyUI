"""
批量视频处理扩展
支持批量上传、切分处理、批量下载视频文件
"""

from .nodes import BatchVideoExtension

# 指定前端扩展目录
WEB_DIRECTORY = "js"

async def comfy_entrypoint() -> BatchVideoExtension:
    return BatchVideoExtension()

__all__ = ["comfy_entrypoint", "WEB_DIRECTORY"]
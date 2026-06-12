import json
import logging
from datetime import UTC, datetime  # UTC 时间格式
from typing import Any

from app.common.middleware import get_request_id, get_trace_id


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式化器 —— 将每条日志记录输出为结构化的 JSON 字符串

    与标准文本格式相比, JSON 格式的优势:
        - 便于日志中心化采集（如 ELK、Loki）和结构化查询
        - 自动关联请求上下文（request_id / trace_id）, 方便分布式链路追踪
        - 时间戳、级别、模块等信息字段化, 避免正则解析
    """

    def format(self, record: logging.LogRecord) -> str:
        """
            格式化日志记录为 JSON 字符串
            @param record: 日志记录对象
            @return: 格式化后的 JSON 字符串表示
        """
        payload: dict[str, Any] = {
            # ISO 8601 格式的时间戳, 含时区信息, 确保跨时区日志排序正确
            "timestamp": datetime.now(UTC).isoformat(),
            # 日志级别 (DEBUG / INFO / WARNING / ERROR / CRITICAL)
            "level": record.levelname,
            # 经过 % 格式化和 exc_info 插值后的完整日志消息
            "message": record.getMessage(),
            # 记录器的名称, 通常是 `__name__`, 用于定位日志来源
            "module": record.name,
            # 从上下文变量中提取当前请求 ID, 串联同一请求的所有日志
            "request_id": get_request_id(),
            # 从上下文变量中提取跟踪 ID, 用于跨服务链路追踪
            "trace_id": get_trace_id(),
        }

        # 如果日志记录包含异常信息, 则附加异常类型和消息到负载中
        # record.exc_info 是一个元组: (exc_type, exc_value, traceback)
        if record.exc_info and record.exc_info[0]:
            # 异常类型, 如 ValueError, KeyError, 不含完整堆栈以避免负载膨胀
            payload["error_type"] = record.exc_info[0].__name__
            # 异常的描述信息, 即 str(exception)
            payload["error_message"] = str(record.exc_info[1])

        # 将字典序列化为 JSON 字符串
        # ensure_ascii=False 允许输出中文等 Unicode 字符, 而非转义为 \uXXXX
        return json.dumps(payload, ensure_ascii=False)
    
def configure_logging(level: str = "INFO") -> None:
    """
        配置全局日志记录器, 并添加 JSON 格式处理程序
        @param level: 日志级别 (DEBUG / INFO / WARNING / ERROR / CRITICAL), 默认 INFO
    """
    root_logger = logging.getLogger() # 获取根记录器
    root_logger.setLevel(level.upper()) # 设置根记录器的日志级别, level.upper() 确保为大写
    
    handler = logging.StreamHandler() # 创建标准输出流处理程序
    handler.setFormatter(JsonFormatter()) # 设置格式化器为 JSON 格式
    
    root_logger.handlers.clear() # 清除根记录器的所有处理程序
    root_logger.addHandler(handler) # 添加标准输出流处理程序到根记录器
        
def get_logger(name: str) -> logging.Logger:
    """
        获取指定名称的日志记录器
        @param name: 记录器名称, 通常是模块名
        @return: 日志记录器对象
    """
    return logging.getLogger(name) # 获取或创建指定名称的日志记录器
        
        
"""
MCP JSON-RPC 2.0 协议处理

定义请求、响应和错误格式。
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

# MCP 协议版本
MCP_PROTOCOL_VERSION = "2024-11-05"


class JSONRPCErrorCode(IntEnum):
    """JSON-RPC 错误码"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class JSONRPCError:
    """JSON-RPC 错误"""
    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def parse_error(cls, message: str = "Parse error") -> 'JSONRPCError':
        return cls(JSONRPCErrorCode.PARSE_ERROR, message)

    @classmethod
    def invalid_request(cls, message: str = "Invalid request") -> 'JSONRPCError':
        return cls(JSONRPCErrorCode.INVALID_REQUEST, message)

    @classmethod
    def method_not_found(cls, method: str) -> 'JSONRPCError':
        return cls(JSONRPCErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}")

    @classmethod
    def invalid_params(cls, message: str) -> 'JSONRPCError':
        return cls(JSONRPCErrorCode.INVALID_PARAMS, message)

    @classmethod
    def internal_error(cls, message: str) -> 'JSONRPCError':
        return cls(JSONRPCErrorCode.INTERNAL_ERROR, message)


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 请求"""
    jsonrpc: str
    method: str
    id: str | int | None = None
    params: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> 'JSONRPCRequest':
        """从字典创建请求"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            id=data.get("id"),
            params=data.get("params"),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.id is not None:
            result["id"] = self.id
        if self.params is not None:
            result["params"] = self.params
        return result

    @property
    def is_notification(self) -> bool:
        """是否为通知（无需响应）"""
        return self.id is None


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 响应"""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: JSONRPCError | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        d = {"jsonrpc": self.jsonrpc}

        if self.id is not None:
            d["id"] = self.id

        if self.error is not None:
            # 支持 error 为 dict 或 JSONRPCError 对象
            if isinstance(self.error, dict):
                d["error"] = self.error
            else:
                d["error"] = self.error.to_dict()
        elif self.result is not None:
            d["result"] = self.result
        else:
            d["result"] = {}

        return d

    @classmethod
    def success(cls, id: str | int | None, result: Any) -> 'JSONRPCResponse':
        """创建成功响应"""
        return cls(id=id, result=result)

    @classmethod
    def make_error(cls, id: str | int | None, error: JSONRPCError) -> 'JSONRPCResponse':
        """创建错误响应"""
        return cls(id=id, error=error)

    @classmethod
    def from_exception(cls, id: str | int | None, e: Exception) -> 'JSONRPCResponse':
        """从异常创建错误响应"""
        return cls(id=id, error=JSONRPCError.internal_error(str(e)))

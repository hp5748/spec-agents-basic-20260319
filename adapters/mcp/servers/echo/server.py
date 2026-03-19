#!/usr/bin/env python3
"""
Echo MCP Server

一个简单的 MCP Server，提供 echo 工具用于测试。

使用方式：
    python server.py

测试：
    使用 MCP 客户端连接后，调用 echo 工具。
"""

import asyncio
import json
import sys
from typing import Any, Dict


class EchoServer:
    """Echo MCP Server"""

    SERVER_INFO = {
        "name": "echo-server",
        "version": "1.0.0",
    }

    PROTOCOL_VERSION = "2024-11-05"

    CAPABILITIES = {
        "tools": {"supported": True},
    }

    async def run(self):
        """运行服务器"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol,
            sys.stdin
        )

        writer = asyncio.StreamWriter(
            protocol=protocol,
            reader=reader,
            loop=asyncio.get_event_loop(),
        )

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break

                request = json.loads(line.decode().strip())
                response = await self.handle_request(request)

                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()

            except json.JSONDecodeError as e:
                await self.send_error(writer, -32700, f"Parse error: {e}")
            except Exception as e:
                await self.send_error(writer, -32603, f"Internal error: {e}")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        handlers = {
            "initialize": self.handle_initialize,
            "tools/list": self.handle_tools_list,
            "tools/call": self.handle_tools_call,
        }

        handler = handlers.get(method)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        try:
            result = await handler(params)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": self.SERVER_INFO,
            "capabilities": self.CAPABILITIES,
        }

    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "tools": [
                {
                    "name": "echo",
                    "description": "返回输入的消息",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "要回显的消息"
                            }
                        },
                        "required": ["message"]
                    }
                },
                {
                    "name": "reverse",
                    "description": "反转输入的字符串",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "要反转的文本"
                            }
                        },
                        "required": ["text"]
                    }
                }
            ]
        }

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "echo":
            message = arguments.get("message", "")
            return {
                "content": [
                    {"type": "text", "text": f"Echo: {message}"}
                ]
            }

        elif tool_name == "reverse":
            text = arguments.get("text", "")
            reversed_text = text[::-1]
            return {
                "content": [
                    {"type": "text", "text": reversed_text}
                ]
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def send_error(self, writer, code: int, message: str):
        """发送错误响应"""
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": code, "message": message}
        }
        writer.write((json.dumps(response) + "\n").encode())
        await writer.drain()


def main():
    """主入口"""
    server = EchoServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch MCP Server

提供 HTTP 请求能力的 MCP Server。

使用方式：
    python server.py

工具：
    - fetch: 获取 URL 内容
    - post: 发送 POST 请求
"""

import asyncio
import json
import sys
from typing import Any, Dict


class FetchServer:
    """Fetch MCP Server"""

    SERVER_INFO = {
        "name": "fetch-server",
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
                    "name": "fetch",
                    "description": "获取 URL 内容",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "要获取的 URL"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "最大返回长度",
                                "default": 5000
                            }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "post",
                    "description": "发送 POST 请求",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "目标 URL"
                            },
                            "body": {
                                "type": "object",
                                "description": "请求体（JSON）"
                            },
                            "headers": {
                                "type": "object",
                                "description": "请求头"
                            }
                        },
                        "required": ["url"]
                    }
                }
            ]
        }

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "fetch":
            return await self._fetch(arguments)
        elif tool_name == "post":
            return await self._post(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _fetch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行 GET 请求"""
        import httpx

        url = args.get("url")
        max_length = args.get("max_length", 5000)

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            content = response.text[:max_length]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"URL: {url}\nStatus: {response.status_code}\n\n{content}"
                    }
                ]
            }

    async def _post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行 POST 请求"""
        import httpx

        url = args.get("url")
        body = args.get("body", {})
        headers = args.get("headers", {})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=body,
                headers=headers,
                timeout=30.0
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"URL: {url}\nStatus: {response.status_code}\n\n{response.text[:5000]}"
                    }
                ]
            }

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
    server = FetchServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

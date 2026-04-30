"""
FastAPI 应用入口

提供 Web 服务，包括：
- 静态文件服务（前端界面）
- 聊天 API（流式/非流式）
- 会话管理 API
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .routes import chat_router, session_router
from ..memory import get_memory_manager
from ..agent.skill_registry import register_skills_to_registry


logger = logging.getLogger(__name__)

# 静态文件目录
STATIC_DIR = Path(__file__).parent.parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在初始化服务...")

    # 初始化记忆管理器
    memory_manager = get_memory_manager()
    await memory_manager.initialize()

    # 注册 Skills 到 ToolRegistry
    from pathlib import Path
    skills_dir = Path(__file__).parent.parent.parent / "skills"
    registered = register_skills_to_registry(str(skills_dir))
    logger.info(f"已注册 {len(registered)} 个 Skills: {registered}")

    # 注册 SubAgents 到 ToolRegistry
    try:
        from ..subagent.config import SubAgentLoader
        from ..agent.tool import Tool, ToolType, ToolParameter, ToolResult
        from ..agent.tool_registry import get_global_registry

        project_root = str(Path(__file__).parent.parent.parent)
        loader = SubAgentLoader(project_root)
        loaded_agents = loader.scan_and_load()
        registry = get_global_registry()

        for name, agent_instance in loaded_agents.items():
            # 为每个 SubAgent 创建异步 handler
            def make_handler(agent):
                async def handler(**kwargs):
                    from ...subagent.base_agent import SubAgentInput
                    input_data = SubAgentInput(
                        query=kwargs.get("query", str(kwargs)),
                        session_id=kwargs.get("session_id", "default"),
                    )
                    result = await agent.process(input_data)
                    return ToolResult(
                        success=result.success,
                        data=result.response if result.success else None,
                        error=result.error,
                    )
                return handler

            tool = Tool(
                name=f"subagent.{name}",
                type=ToolType.SUBAGENT,
                description=agent_instance.config.description,
                handler=make_handler(agent_instance),
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description=f"发送给 {name} Agent 的查询内容",
                        required=True,
                    )
                ],
            )
            registry.register_tool(tool)
            logger.info(f"已注册 SubAgent: {name}")

        if loaded_agents:
            logger.info(f"已注册 {len(loaded_agents)} 个 SubAgents: {list(loaded_agents.keys())}")
    except Exception as e:
        logger.warning(f"SubAgent 注册失败（非致命）: {e}")

    logger.info("服务初始化完成")

    yield

    # 关闭时清理
    logger.info("正在关闭服务...")
    await memory_manager.cleanup()
    logger.info("服务已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Super Agent",
        description="智能对话 Agent，支持流式对话、记忆管理和 Skill 调用",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    app.include_router(chat_router)
    app.include_router(session_router)

    # 挂载静态文件
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"静态文件目录: {STATIC_DIR}")

    # 首页路由
    @app.get("/", response_class=FileResponse)
    async def index():
        """返回首页"""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Super Agent API", "docs": "/docs"}

    # 健康检查
    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "healthy"}

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 启动服务
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

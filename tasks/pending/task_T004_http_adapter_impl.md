# 任务卡

## 基本信息
- **任务ID**: T004
- **标题**: HTTP Adapter 实现
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T002

## 背景说明

### 问题描述
需要实现 REST API 客户端，支持调用外部 HTTP 服务。

### 核心目标
提供通用的 HTTP 调用能力，支持各种 REST API。

## 任务描述

实现 HTTP Adapter，包括：

1. **HTTP 客户端核心**
   - 继承 `BaseAdapter`
   - 实现 `execute()` 方法
   - 支持 GET/POST/PUT/DELETE

2. **配置驱动**
   - 从 `config/adapters.yaml` 加载配置
   - 支持多端点配置
   - 支持认证（API Key/Bearer Token）

3. **请求处理**
   - URL 模板替换
   - 请求头设置
   - 请求体序列化

4. **响应处理**
   - 状态码检查
   - 响应体解析
   - 错误重试

## 技术约束

- 使用 `httpx` 或 `aiohttp` 异步 HTTP 客户端
- 超时控制
- 连接池管理

## 验收标准
- [ ] 支持所有标准 HTTP 方法
- [ ] 认证机制完善
- [ ] 错误处理友好
- [ ] 连接池管理有效

## 输出产物
- [ ] 产物1: `src/adapters/http/client.py` - HTTP 客户端
- [ ] 产物2: `src/adapters/http/config.py` - 配置加载器
- [ ] 产物3: `tests/test_http_adapter.py` - 单元测试

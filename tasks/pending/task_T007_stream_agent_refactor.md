# 任务卡

## 基本信息
- **任务ID**: T007
- **标题**: StreamAgent 重构
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T001, T002, T008

## 背景说明

### 问题描述
需要废弃 IntentRecognizer，基于 Function Calling 重写 StreamAgent。

### 核心目标
实现真正的 LLM 驱动决策，让大模型自主选择工具。

## 任务描述

重构 StreamAgent，包括：

1. **移除意图识别**
   - 删除 IntentRecognizer 调用
   - 删除硬编码优先级规则
   - 删除 `src/intent/` 目录

2. **Function Calling 集成**
   - 从 ToolRegistry 获取工具列表
   - 构建 tools 参数（OpenAPI 格式）
   - 处理 tool_calls 响应

3. **执行流程重构**
   ```
   用户输入 → 构建上下文 → LLM 请求（带 tools）
   ↓
   LLM 返回 tool_calls
   ↓
   AdapterFactory 执行工具
   ↓
   收集结果 → 再次请求 LLM 总结
   ↓
   流式输出
   ```

4. **错误处理**
   - 工具调用失败降级
   - 超时处理
   - 重试机制

## 技术约束

- DeepSeek-V3.2 Function Calling API
- 异步流式输出
- SSE 协议

## 验收标准
- [ ] 完全移除 IntentRecognizer
- [ ] LLM 能自主选择工具
- [ ] 工具调用结果正确融入响应
- [ ] 流式输出正常

## 输出产物
- [ ] 产物1: `src/agent/stream_agent.py` - 重构后的 StreamAgent
- [ ] 产物2: `src/llm_client.py` - 扩展支持 tools 参数
- [ ] 产物3: 删除 `src/intent/` 目录
- [ ] 产物4: `tests/test_stream_agent.py` - 集成测试

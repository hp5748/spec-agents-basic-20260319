# 编码规范

本文档定义了 Skill 相关的编码规范。

## 命名规范

### 文件命名
- 组件文件：PascalCase（如 `UserProfile.tsx`）
- 工具函数：camelCase（如 `formatDate.ts`）
- 常量：UPPER_SNAKE_CASE（如 `API_ENDPOINTS.ts`）

### 变量命名
- 变量：camelCase
- 常量：UPPER_SNAKE_CASE
- 类型/接口：PascalCase

## 代码风格

### 导入顺序
1. 外部依赖
2. 内部模块
3. 类型导入
4. 样式导入

### 函数长度
- 单个函数不超过 50 行
- 超过 20 行考虑拆分

## 禁用词表

以下术语在代码中应避免使用：
- `any`（类型）
- `TODO`（必须有 issue 编号）
- `console.log`（生产代码）
- `var`（使用 `const`/`let`）

## 检查清单

- [ ] 类型定义完整
- [ ] 无 any 类型
- [ ] 函数有注释
- [ ] 通过 lint 检查

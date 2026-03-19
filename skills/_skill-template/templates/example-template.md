# 模板示例

这是一个模板文件示例。

## 用途

- 作为 Skill 输出的格式参考
- 提供标准化的输出结构

## 模板内容

```typescript
// {{componentName}}.tsx
import React from 'react';

interface {{ComponentName}}Props {
  // 添加属性
}

export const {{ComponentName}}: React.FC<{{ComponentName}}Props> = (props) => {
  return (
    <div>
      {/* 组件内容 */}
    </div>
  );
};
```

## 使用说明

1. 复制模板内容
2. 替换 `{{componentName}}` 占位符
3. 添加具体实现

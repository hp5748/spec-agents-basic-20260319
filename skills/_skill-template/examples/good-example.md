# 优秀示例

这是一个正确的实现示例。

## 代码

```typescript
// GoodComponent.tsx
import React from 'react';

interface GoodComponentProps {
  title: string;
  onClick?: () => void;
}

export const GoodComponent: React.FC<GoodComponentProps> = ({
  title,
  onClick
}) => {
  return (
    <button onClick={onClick}>
      {title}
    </button>
  );
};
```

## 为什么好

1. ✅ 清晰的类型定义
2. ✅ 解构 props
3. ✅ 可选属性使用 `?`
4. ✅ 简洁的组件结构

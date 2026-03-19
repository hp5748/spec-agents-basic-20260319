# 反模式示例

这是一个**错误**的实现示例，请避免。

## 代码

```typescript
// BadComponent.tsx
// ❌ 没有类型定义
export const BadComponent = (props) => {
  // ❌ 直接使用 props 而不解构
  // ❌ 使用 any 类型
  const handleClick: any = () => {
    props.onClick();
  };

  return (
    // ❌ 内联样式
    <button style={{color: 'red'}} onClick={handleClick}>
      {props.title}
    </button>
  );
};
```

## 为什么不好

1. ❌ 缺少类型定义
2. ❌ 使用 `any` 类型
3. ❌ 未解构 props
4. ❌ 内联样式

## 正确做法

参见 [good-example.md](./good-example.md)

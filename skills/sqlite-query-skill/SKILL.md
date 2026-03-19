---
name: sqlite-query-skill
description: SQLite 数据库查询技能，支持人员信息查询
version: 1.0.0
priority: 10
intents:
  - database_query
  - person_search
keywords:
  - 查询
  - 数据库
  - SQLite
  - 人员
  - 搜索
  - 找
examples:
  - "查询张三的信息"
  - "搜索姓李的员工"
  - "找一下技术部的同事"
  - "查询 IT 部门的员工"
---

# SQLite 查询技能

## 功能说明

这个技能允许用户通过自然语言查询 SQLite 数据库中的人员信息。

## 支持的查询类型

1. **按姓名搜索**: 搜索包含指定姓名的人员
2. **按部门搜索**: 查询指定部门的所有员工
3. **按职位搜索**: 查询指定职位的员工
4. **列出所有**: 列出数据库中所有人员

## 使用方式

- "查询张三的信息" - 按姓名搜索
- "搜索技术部的员工" - 按部门搜索
- "查询工程师职位的同事" - 按职位搜索
- "列出所有人员" - 列出所有

## 数据库结构

表名: `persons`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 姓名 |
| department | TEXT | 部门 |
| position | TEXT | 职位 |
| email | TEXT | 邮箱 |
| phone | TEXT | 电话 |
| hire_date | TEXT | 入职日期 |

## 注意事项

- 这是一个只读技能，不支持修改数据
- 查询结果最多返回 10 条记录
- 支持模糊匹配（姓名、部门、职位）

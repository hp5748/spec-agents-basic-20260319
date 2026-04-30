---
name: big-data-study
description: 大数据技术学习助手，提供结构化课程大纲、模块详解、练习题和知识点讲解
version: 1.0.0
tags: [big_data, study, education, hadoop, spark]
priority: 10
intents:
  - study_big_data
  - learn_big_data
  - big_data_course
keywords:
  - 大数据
  - Hadoop
  - Spark
  - HDFS
  - MapReduce
  - Hive
  - Kafka
  - 学习
  - 课程
  - 练习
  - 测试
  - 考试
examples:
  - "我想学习大数据"
  - "大数据有哪些技术"
  - "介绍一下 Hadoop"
  - "Spark 和 MapReduce 的区别"
  - "给我出几道大数据的题"
  - "HDFS 读写流程是什么"
  - "大数据学习路线"
---

# 大数据学习助手

## 功能

提供结构化的大数据技术学习内容和练习。支持课程大纲浏览、模块详解、练习测试、知识点深度讲解。

## 使用方式

根据用户需求选择合适的 action 参数调用此工具：

| 用户意图 | action | 额外参数 |
|---------|--------|---------|
| 想了解大数据学什么 / 学习路线 | `outline` | 无 |
| 想深入了解某个模块 | `detail` | `module`（模块 ID） |
| 想做练习 / 测试 | `quiz` | `module`（模块 ID） |
| 问具体技术概念 | `explain` | `topic`（知识点 ID） |
| 想看学习进度 | `progress` | `completed_modules`（已学模块，逗号分隔） |

## 多轮对话策略

1. **首次接触**：用户说"学大数据"时，先调用 `outline` 展示全貌
2. **逐步深入**：用户选择模块后，调用 `detail` 讲解，每次只教一个模块
3. **巩固练习**：每个模块教完后建议做 `quiz` 检验学习效果
4. **概念追问**：用户问具体问题时，调用 `explain` 给出深度讲解
5. **进度跟踪**：用户想回顾时，调用 `progress` 汇总已完成模块

## 可用 module 值

`overview`（大数据概述）、`hadoop`（Hadoop 生态）、`hdfs`（HDFS 存储）、`mapreduce`（MapReduce）、`spark`（Spark）、`hive`（Hive）、`kafka`（Kafka）

## 可用 topic 值（用于 explain）

`hdfs_read_write`（HDFS 读写流程）、`map_reduce_shuffle`（MapReduce Shuffle）、`spark_rdd`（Spark RDD）、`hive_vs_rdbms`（Hive 与关系数据库）、`kafka_architecture`（Kafka 架构）

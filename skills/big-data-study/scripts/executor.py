"""
大数据学习助手 - 执行器

提供结构化的大数据技术学习内容，支持多轮递进式学习。
内置完整知识库，无需外部数据源。

支持 5 种 action：
- outline: 课程大纲
- detail: 模块详解
- quiz: 练习题
- explain: 知识点深度讲解
- progress: 学习进度报告
"""

from typing import Any, Dict, List

# =============================================================================
# 内置知识库
# =============================================================================

MODULES = [
    {"id": "overview", "name": "大数据概述", "duration": "1小时",
     "desc": "了解大数据的基本概念、5V 特征和应用场景"},
    {"id": "hadoop", "name": "Hadoop 生态系统", "duration": "3小时",
     "desc": "掌握 Hadoop 三剑客（HDFS + MapReduce + YARN）及生态组件"},
    {"id": "hdfs", "name": "HDFS 分布式存储", "duration": "2小时",
     "desc": "深入理解 HDFS 架构、读写流程和副本机制"},
    {"id": "mapreduce", "name": "MapReduce 计算框架", "duration": "3小时",
     "desc": "学习分布式计算编程模型和 Shuffle 过程"},
    {"id": "spark", "name": "Spark 内存计算", "duration": "3小时",
     "desc": "掌握 Spark Core、RDD/DataFrame 和对比 MapReduce 的优势"},
    {"id": "hive", "name": "Hive 数据仓库", "duration": "2小时",
     "desc": "学习 SQL-on-Hadoop 和数据仓库设计"},
    {"id": "kafka", "name": "Kafka 消息队列", "duration": "2小时",
     "desc": "理解发布订阅模型、分区副本和流处理应用"},
]

MODULE_DETAILS = {
    "overview": {
        "title": "大数据概述",
        "concepts": [
            "大数据的 5V 特征：Volume（大量）、Velocity（高速）、Variety（多样）、Value（低价值密度）、Veracity（真实性）",
            "大数据技术栈全景：数据采集 → 数据存储 → 数据计算 → 数据分析 → 数据可视化",
            "核心应用场景：用户画像、推荐系统、风控反欺诈、日志分析、物联网数据处理",
            "传统数据处理 vs 大数据处理的区别（GB 级 → PB 级）",
        ],
        "key_points": [
            "大数据不仅仅是数据量大，更强调处理方式和思维方式的转变",
            "Google 三篇论文（GFS、MapReduce、BigTable）是大数据技术的理论基石",
            "Lambda 架构和 Kappa 架构是两种主流的大数据处理架构",
        ],
    },
    "hadoop": {
        "title": "Hadoop 生态系统",
        "concepts": [
            "Hadoop 三剑客：HDFS（存储）+ MapReduce（计算）+ YARN（资源管理）",
            "HDFS：分布式文件系统，提供高吞吐量的数据访问",
            "MapReduce：分布式并行计算框架，分而治之",
            "YARN：Yet Another Resource Negotiator，统一资源管理和调度",
            "生态组件：Hive（SQL查询）、HBase（NoSQL）、ZooKeeper（协调）、Flume（采集）、Sqoop（导入导出）",
        ],
        "key_points": [
            "Hadoop 的核心思想是将计算移向数据，而非将数据移向计算",
            "NameNode 是 HDFS 的主节点，负责元数据管理（单点问题，可通过 HA 解决）",
            "YARN 使得 Hadoop 从单一 MapReduce 平台变为通用资源管理平台",
            "Hadoop 适用场景：离线批处理、大规模数据分析、日志处理",
        ],
    },
    "hdfs": {
        "title": "HDFS 分布式存储",
        "concepts": [
            "架构：NameNode（主节点，管理元数据）+ DataNode（数据节点，存储数据块）",
            "数据块（Block）：默认 128MB，大块减少寻址开销",
            "副本机制：默认 3 副本（本地 → 同机架 → 跨机架），保证容错",
            "读写流程：读数据通过 NameNode 获取块位置 → 最近 DataNode 读取；写数据通过 pipeline 流式写入",
            "HA 高可用：Active/Standby NameNode + ZooKeeper 自动故障转移",
        ],
        "key_points": [
            "HDFS 优化了「一次写入、多次读取」的顺序读场景，不适合低延迟随机访问",
            "副本放置策略（Rack Awareness）：提升数据可靠性和读取带宽",
            "Secondary NameNode 不是 NameNode 的热备，而是辅助合并 EditLog 和 FsImage",
        ],
    },
    "mapreduce": {
        "title": "MapReduce 计算框架",
        "concepts": [
            "编程模型：Map（分片处理）→ Shuffle（排序分组）→ Reduce（聚合汇总）",
            "Map 阶段：InputSplit → RecordReader → Map 函数 → 输出 <Key, Value> 对",
            "Shuffle 阶段：Partition（分区）→ Sort（排序）→ Group（分组）→ Combine（可选本地聚合）",
            "Reduce 阶段：拉取 Map 输出 → Merge → Reduce 函数 → 输出结果",
            "WordCount 经典示例：统计文本中每个单词的出现次数",
        ],
        "key_points": [
            "MapReduce 的核心是自动并行化和分布式执行，开发者只需关注 Map/Reduce 逻辑",
            "Shuffle 是性能瓶颈，大量数据在节点间传输",
            "Combiner 可以在 Map 端做局部聚合，减少 Shuffle 数据量",
            "MapReduce 不适合迭代计算（如机器学习），每轮需要读写磁盘",
        ],
    },
    "spark": {
        "title": "Spark 内存计算",
        "concepts": [
            "RDD（Resilient Distributed Dataset）：弹性分布式数据集，Spark 的核心抽象",
            "DataFrame/Dataset：类似关系表的结构化数据抽象，支持 SQL 查询",
            "内存计算：中间结果缓存在内存中，避免 MapReduce 每轮写磁盘的问题",
            "Spark 生态：Spark SQL、Spark Streaming、MLlib（机器学习）、GraphX（图计算）",
            "DAG 执行引擎：将任务构建为有向无环图，比 MapReduce 的两阶段模型更灵活",
        ],
        "key_points": [
            "Spark 比 MapReduce 快 10-100 倍（内存计算 + DAG 优化）",
            "RDD 的转换（Transformation）是懒加载的，只有行动（Action）才触发计算",
            "Spark 的宽依赖（Shuffle）和窄依赖决定了 Stage 的划分",
            "Spark 3.x 引入了 AQE（自适应查询执行），运行时动态优化执行计划",
        ],
    },
    "hive": {
        "title": "Hive 数据仓库",
        "concepts": [
            "SQL-on-Hadoop：用类 SQL 语言（HQL）查询 HDFS 上的数据",
            "元数据管理：Metastore 存储表结构、分区、列信息（通常用 MySQL）",
            "执行引擎：HQL → 编译优化 → 生成 MapReduce/Tez/Spark 任务",
            "数据模型：Database → Table（内部表/外部表）→ Partition → Bucket",
            "文件格式：TextFile、SequenceFile、ORC（推荐）、Parquet",
        ],
        "key_points": [
            "Hive 适用于离线批处理（OLAP），不适用于实时查询（OLTP）",
            "外部表（EXTERNAL TABLE）删除时不删数据，内部表删除时数据也会被删",
            "分区（Partition）是 Hive 性能优化的核心手段，按分区裁剪减少扫描量",
            "ORC 格式支持列式存储、压缩和谓词下推，性能远优于 TextFile",
        ],
    },
    "kafka": {
        "title": "Kafka 消息队列",
        "concepts": [
            "发布订阅模型：Producer → Topic（分区）→ Consumer Group → Consumer",
            "分区（Partition）：Topic 被分为多个分区，分布在不同 Broker 上，支持并行消费",
            "副本（Replica）：每个分区有多个副本（Leader + Follower），保证高可用",
            "Consumer Group：同一组内的 Consumer 分摊分区消费，实现负载均衡",
            "消息持久化：消息写入磁盘日志（Log），通过 Offset 管理消费位置",
        ],
        "key_points": [
            "Kafka 的核心设计是顺序写磁盘 + 零拷贝（Zero-Copy），吞吐量极高",
            "消费者通过 Offset 控制消费进度，可以重置 Offset 重新消费",
            "分区数决定了最大并行度（Consumer 数不能超过分区数）",
            "Kafka 2.8+ 支持 KRaft 模式（无需 ZooKeeper），简化部署",
        ],
    },
}

QUIZZES = {
    "overview": [
        {"type": "choice", "question": "大数据的 5V 特征中，'V' 代表 Velocity 指的是？",
         "options": ["数据量大", "数据处理速度快", "数据种类多", "数据真实性"], "answer": "B"},
        {"type": "choice", "question": "以下哪个不是大数据的典型应用场景？",
         "options": ["用户画像", "推荐系统", "手工记账", "风控反欺诈"], "answer": "C"},
        {"type": "short", "question": "简述 Google 三篇论文分别对应的大数据技术",
         "answer": "GFS → HDFS（分布式文件系统）、MapReduce → Hadoop MapReduce（分布式计算）、BigTable → HBase（分布式数据库）"},
    ],
    "hadoop": [
        {"type": "choice", "question": "Hadoop 的核心组件不包括以下哪个？",
         "options": ["HDFS", "MapReduce", "Spark", "YARN"], "answer": "C"},
        {"type": "choice", "question": "YARN 的全称是什么？",
         "options": ["Yet Another Resource Negotiator", "You Are Resource Navigator",
                      "Yield Application Resource Network", "Yet Another Runtime Name"], "answer": "A"},
        {"type": "short", "question": "简述 Hadoop '将计算移向数据' 的设计思想",
         "answer": "传统方式将数据传输到计算节点，大数据场景下传输成本极高。Hadoop 将计算任务调度到数据所在节点执行，利用数据本地性减少网络传输，提高效率。"},
    ],
    "hdfs": [
        {"type": "choice", "question": "HDFS 默认的数据块大小是？",
         "options": ["64MB", "128MB", "256MB", "512MB"], "answer": "B"},
        {"type": "choice", "question": "HDFS 默认的副本数是？",
         "options": ["1", "2", "3", "5"], "answer": "C"},
        {"type": "short", "question": "Secondary NameNode 的作用是什么？它是不是 NameNode 的热备？",
         "answer": "Secondary NameNode 定期合并 EditLog 和 FsImage（检查点），防止 EditLog 过大。它不是 NameNode 的热备，HA 需要通过 Active/Standby NameNode + ZooKeeper 实现。"},
    ],
    "mapreduce": [
        {"type": "choice", "question": "MapReduce 中，哪个阶段是性能瓶颈？",
         "options": ["Map 阶段", "Shuffle 阶段", "Reduce 阶段", "Input 阶段"], "answer": "B"},
        {"type": "choice", "question": "Combiner 的作用是什么？",
         "options": ["对 Map 输出做全局聚合", "对 Map 输出做局部聚合，减少 Shuffle 数据量",
                      "对 Reduce 输出做排序", "合并多个 InputSplit"], "answer": "B"},
        {"type": "short", "question": "为什么 MapReduce 不适合迭代计算（如机器学习）？",
         "answer": "MapReduce 每个 Job 的中间结果需要写入磁盘（HDFS），迭代计算需要多轮 MapReduce，大量磁盘 I/O 导致效率极低。Spark 通过内存缓存 RDD 解决了这个问题。"},
    ],
    "spark": [
        {"type": "choice", "question": "Spark 的核心数据抽象是？",
         "options": ["DataFrame", "RDD", "Dataset", "Table"], "answer": "B"},
        {"type": "choice", "question": "RDD 的 Transformation 操作的特点是？",
         "options": ["立即执行", "懒加载（延迟执行）", "只支持单机", "不支持链式调用"], "answer": "B"},
        {"type": "short", "question": "Spark 比 MapReduce 快的主要原因是什么？",
         "answer": "1）内存计算：中间结果缓存在内存，避免每轮写磁盘；2）DAG 执行引擎：将任务构建为有向无环图，减少不必要的 Stage 划分；3）多线程模型：每个 Task 在线程中执行，MapReduce 是进程级。"},
    ],
    "hive": [
        {"type": "choice", "question": "删除外部表（EXTERNAL TABLE）时，数据会怎样？",
         "options": ["数据被删除", "数据保留，只删除元数据", "数据被移动到回收站", "报错，不允许删除"], "answer": "B"},
        {"type": "choice", "question": "以下哪种 Hive 文件格式性能最好？",
         "options": ["TextFile", "SequenceFile", "ORC", "CSV"], "answer": "C"},
        {"type": "short", "question": "Hive 分区（Partition）的作用和原理",
         "answer": "分区是将表数据按某个字段的值分目录存储（如按日期 /year=2024/month=01/）。查询时通过 WHERE 条件裁剪分区，只扫描相关目录，避免全表扫描，大幅提升查询性能。"},
    ],
    "kafka": [
        {"type": "choice", "question": "Kafka 中 Consumer Group 的特性是？",
         "options": ["一个分区可被同组多个消费者消费", "一个分区只能被同组一个消费者消费",
                      "消费者数不能超过 Broker 数", "消费者组之间共享 Offset"], "answer": "B"},
        {"type": "choice", "question": "Kafka 实现高吞吐量的核心技术是？",
         "options": ["随机写磁盘", "内存缓存 + 异步刷盘", "顺序写磁盘 + 零拷贝", "多线程并发写入"], "answer": "C"},
        {"type": "short", "question": "Kafka 的分区数对系统有什么影响？",
         "answer": "分区数决定了最大并行度：同一 Consumer Group 内的 Consumer 数不能超过分区数，多余的 Consumer 会闲置。分区越多，并行度越高，但也会增加 Broker 的文件句柄和内存开销。"},
    ],
}

EXPLANATIONS = {
    "hdfs_read_write": {
        "title": "HDFS 读写流程详解",
        "content": (
            "## HDFS 读流程\n\n"
            "1. 客户端调用 `open()` 打开文件\n"
            "2. 从 NameNode 获取文件的数据块列表和每个块的 DataNode 位置\n"
            "3. 选择距离最近的 DataNode 副本（Rack Awareness 优化）\n"
            "4. 建立数据传输通道，顺序读取数据块\n"
            "5. 当前块读完，切换到下一个块的最近 DataNode\n"
            "6. 所有块读取完成，调用 `close()`\n\n"
            "## HDFS 写流程\n\n"
            "1. 客户端调用 `create()` 创建文件\n"
            "2. NameNode 检查权限和路径，创建文件记录\n"
            "3. 客户端将数据分成 Packet（默认 64KB）\n"
            "4. 建立 Pipeline：Client → DataNode1 → DataNode2 → DataNode3\n"
            "5. 数据以流水线方式写入 3 个副本（Streaming）\n"
            "6. ACK 确认队列确保所有副本写入成功\n"
            "7. 所有数据写入完成，调用 `close()` 通知 NameNode\n\n"
            "**关键概念**：Pipeline 写入是 HDFS 高性能的关键——数据像流水线一样依次流过"
            "各个 DataNode，而非客户端向每个 DataNode 单独发送完整副本。"
        ),
    },
    "map_reduce_shuffle": {
        "title": "MapReduce Shuffle 过程详解",
        "content": (
            "## Shuffle 是什么\n\n"
            "Shuffle 是 Map 输出到 Reduce 输入之间的数据传输和重组过程，"
            "是 MapReduce 性能的关键瓶颈。\n\n"
            "## Shuffle 四步骤\n\n"
            "### 1. Partition（分区）\n"
            "- 根据 Key 的 Hash 值决定数据发送到哪个 Reducer\n"
            "- 公式：`partition = hash(key) % numReduceTasks`\n"
            "- 保证相同 Key 的数据发送到同一个 Reducer\n\n"
            "### 2. Sort（排序）\n"
            "- 每个 Map Task 的输出按 Key 排序\n"
            "- 排序在内存中进行（溢写时排序）\n\n"
            "### 3. Combine（可选，本地聚合）\n"
            "- 在 Map 端对相同 Key 做局部聚合\n"
            "- 减少 Shuffle 传输的数据量\n"
            "- 示例：WordCount 中 Map 端先统计一次词频\n\n"
            "### 4. Group（分组）\n"
            "- Reduce 端拉取所有 Map 的对应分区数据\n"
            "- 合并排序后，相同 Key 的 Value 形成一个迭代器\n"
            "- 传给 `reduce(Key, Iterable<Values>)` 方法\n\n"
            "**性能优化关键**：减少 Shuffle 数据量 = 提升整体性能"
        ),
    },
    "spark_rdd": {
        "title": "Spark RDD 详解",
        "content": (
            "## RDD（Resilient Distributed Dataset）\n\n"
            "弹性分布式数据集，Spark 最核心的数据抽象。\n\n"
            "### 核心特性\n"
            "- **不可变（Immutable）**：创建后不可修改，每次转换产生新 RDD\n"
            "- **分区（Partitioned）**：数据分布在集群多个节点上\n"
            "- **容错（Resilient）**：通过血缘（Lineage）自动重建丢失的分区\n\n"
            "### 两种操作\n"
            "- **Transformation（转换）**：懒加载，不立即执行\n"
            "  - `map()`, `filter()`, `flatMap()`, `groupByKey()`, `reduceByKey()`\n"
            "- **Action（行动）**：触发实际计算\n"
            "  - `collect()`, `count()`, `save()`, `foreach()`\n\n"
            "### 容错机制\n"
            "- RDD 记录血缘关系（从创建到当前的所有转换操作链）\n"
            "- 分区丢失时，根据血缘重新计算（无需数据复制）\n\n"
            "### 宽依赖 vs 窄依赖\n"
            "- **窄依赖**：父分区最多被一个子分区使用（如 map、filter）\n"
            "- **宽依赖**：父分区被多个子分区使用（如 groupByKey）→ 触发 Shuffle → 划分 Stage 边界\n\n"
            "**建议**：实际开发优先使用 DataFrame/Dataset API，比 RDD 更高效（有 Catalyst 优化器和 Tungsten 执行引擎）。"
        ),
    },
    "hive_vs_rdbms": {
        "title": "Hive 与关系数据库对比",
        "content": (
            "## Hive vs RDBMS 核心区别\n\n"
            "| 维度 | Hive | RDBMS（MySQL 等） |\n"
            "|------|------|------------------|\n"
            "| 数据规模 | PB 级 | GB~TB 级 |\n"
            "| 查询延迟 | 分钟~小时级 | 毫秒~秒级 |\n"
            "| 数据更新 | 批量追加为主 | 随机增删改查 |\n"
            "| 执行引擎 | MapReduce/Tez/Spark | 自有引擎 |\n"
            "| 索引 | 有限支持 | 丰富（B+Tree、Hash等） |\n"
            "| 事务 | 有限支持（ACID） | 完整 ACID |\n"
            "| 适用场景 | OLAP 离线分析 | OLTP 在线事务 |\n\n"
            "## Hive 的独特优势\n\n"
            "1. **处理海量数据**：分布式执行，线性扩展\n"
            "2. **SQL 接口**：降低大数据使用门槛\n"
            "3. **多引擎**：可切换 MapReduce/Tez/Spark\n"
            "4. **与 Hadoop 生态集成**：直接访问 HDFS 数据\n\n"
            "## 典型误区\n\n"
            "- Hive 不是数据库，而是数据仓库工具\n"
            "- Hive SQL 不等于标准 SQL（有一些语法差异和限制）\n"
            "- Hive 不适合实时查询，不要用它替代 MySQL"
        ),
    },
    "kafka_architecture": {
        "title": "Kafka 架构详解",
        "content": (
            "## Kafka 核心架构\n\n"
            "### 组件\n"
            "- **Broker**：Kafka 服务节点，多个 Broker 组成集群\n"
            "- **Topic**：消息分类，逻辑概念\n"
            "- **Partition**：Topic 的物理分片，是并行度的基本单位\n"
            "- **Producer**：消息生产者，向 Topic 发送消息\n"
            "- **Consumer**：消息消费者，从 Topic 拉取消息\n"
            "- **Consumer Group**：消费者组，组内分摊消费\n\n"
            "### 数据存储\n"
            "- 每个分区对应一个日志目录\n"
            "- 消息以追加（Append）方式写入，顺序写磁盘\n"
            "- 使用 Segment 文件 + Index 文件管理\n"
            "- 通过 Offset 定位消息（O(1) 复杂度）\n\n"
            "### 副本机制\n"
            "- 每个 Partition 有多个 Replica\n"
            "- Leader Replica：处理读写请求\n"
            "- Follower Replica：从 Leader 同步数据\n"
            "- Leader 故障时，从 ISR（In-Sync Replicas）中选举新 Leader\n\n"
            "### 高性能原理\n"
            "- **顺序写磁盘**：600MB/s vs 随机写 100KB/s\n"
            "- **零拷贝（Zero-Copy）**：数据从磁盘直接到网卡，不经过用户空间\n"
            "- **批量发送**：Producer 批量压缩发送，减少网络开销\n"
            "- **页缓存（Page Cache）**：利用操作系统缓存，避免 JVM GC 问题"
        ),
    },
}


# =============================================================================
# 格式化函数
# =============================================================================

def format_outline() -> str:
    """格式化课程大纲"""
    lines = ["# 大数据学习课程大纲\n"]
    lines.append("共 7 个模块，建议学习顺序：\n")
    for i, m in enumerate(MODULES, 1):
        lines.append(f"**{i}. {m['name']}** （约 {m['duration']}）")
        lines.append(f"   {m['desc']}\n")
    total = sum(int(m["duration"].replace("小时", "")) for m in MODULES)
    lines.append(f"---\n总计约 **{total} 小时**。回复模块名称或编号即可开始学习。")
    return "\n".join(lines)


def format_detail(module_id: str) -> str:
    """格式化模块详解"""
    if module_id not in MODULE_DETAILS:
        available = ", ".join(m["id"] for m in MODULES)
        return f"未找到模块 '{module_id}'。可用模块：{available}"

    info = MODULE_DETAILS[module_id]
    lines = [f"# {info['title']}\n"]

    lines.append("## 核心概念\n")
    for i, c in enumerate(info["concepts"], 1):
        lines.append(f"{i}. {c}")

    lines.append("\n## 学习要点\n")
    for i, p in enumerate(info["key_points"], 1):
        lines.append(f"- {p}")

    lines.append(f"\n---\n学习完本模块后，可以说「出几道题」来测试学习效果。")
    return "\n".join(lines)


def format_quiz(module_id: str) -> str:
    """格式化练习题"""
    if module_id not in QUIZZES:
        available = ", ".join(QUIZZES.keys())
        return f"未找到模块 '{module_id}' 的练习题。可用模块：{available}"

    quizzes = QUIZZES[module_id]
    lines = [f"# 练习题\n"]

    for i, q in enumerate(quizzes, 1):
        if q["type"] == "choice":
            lines.append(f"**第 {i} 题（选择题）**：{q['question']}")
            for j, opt in enumerate(q["options"]):
                lines.append(f"   {'ABCD'[j]}. {opt}")
            lines.append("")
        elif q["type"] == "short":
            lines.append(f"**第 {i} 题（简答题）**：{q['question']}\n")

    lines.append("---\n**参考答案**（建议先自己做再核对）：\n")
    for i, q in enumerate(quizzes, 1):
        ans = q["answer"]
        if q["type"] == "choice":
            idx = ord(ans) - ord("A")
            lines.append(f"第 {i} 题：**{ans}**. {q['options'][idx]}")
        else:
            lines.append(f"第 {i} 题：{ans}")

    return "\n".join(lines)


def format_explain(topic_id: str) -> str:
    """格式化知识点讲解"""
    if topic_id not in EXPLANATIONS:
        available = ", ".join(EXPLANATIONS.keys())
        return f"未找到知识点 '{topic_id}'。可用知识点：{available}"

    info = EXPLANATIONS[topic_id]
    return f"# {info['title']}\n\n{info['content']}"


def format_progress(completed_str: str) -> str:
    """格式化学习进度"""
    completed = set(completed_str.split(",")) if completed_str else set()
    completed = {c.strip() for c in completed if c.strip()}

    lines = ["# 学习进度报告\n"]

    total = len(MODULES)
    done = len(completed & {m["id"] for m in MODULES})
    pct = int(done / total * 100) if total > 0 else 0

    lines.append(f"总进度：**{done}/{total} 模块**（{pct}%）\n")

    lines.append("## 模块状态\n")
    for m in MODULES:
        status = "✅ 已完成" if m["id"] in completed else "⬜ 未学习"
        lines.append(f"- {status} **{m['name']}** ({m['id']})")

    # 建议下一步
    next_modules = [m for m in MODULES if m["id"] not in completed]
    if next_modules:
        nxt = next_modules[0]
        lines.append(f"\n## 建议\n")
        lines.append(f"下一步建议学习：**{nxt['name']}**")
        lines.append(f"回复「详细介绍 {nxt['id']}」开始学习。")
    else:
        lines.append(f"\n🎉 恭喜！你已经完成了所有模块的学习！")

    return "\n".join(lines)


# =============================================================================
# Skill 入口
# =============================================================================

def execute(context: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Skill 执行入口

    Args:
        context: 运行上下文（session_id 等）
        input_data: 输入参数，支持：
            - action: 执行动作（outline/detail/quiz/explain/progress）
            - module: 模块 ID（detail/quiz 时使用）
            - topic: 知识点 ID（explain 时使用）
            - completed_modules: 已完成模块，逗号分隔（progress 时使用）

    Returns:
        {"success": bool, "response": str, "data": dict}
    """
    action = input_data.get("action", "outline")

    try:
        if action == "outline":
            response = format_outline()
            return {"success": True, "response": response, "data": {"action": "outline"}}

        elif action == "detail":
            module_id = input_data.get("module", "overview")
            response = format_detail(module_id)
            return {"success": True, "response": response, "data": {"action": "detail", "module": module_id}}

        elif action == "quiz":
            module_id = input_data.get("module", "hadoop")
            response = format_quiz(module_id)
            return {"success": True, "response": response, "data": {"action": "quiz", "module": module_id}}

        elif action == "explain":
            topic_id = input_data.get("topic", "")
            if not topic_id:
                available = ", ".join(EXPLANATIONS.keys())
                return {"success": False, "error": f"缺少 topic 参数。可用知识点：{available}"}
            response = format_explain(topic_id)
            return {"success": True, "response": response, "data": {"action": "explain", "topic": topic_id}}

        elif action == "progress":
            completed_str = input_data.get("completed_modules", "")
            response = format_progress(completed_str)
            return {"success": True, "response": response, "data": {"action": "progress"}}

        else:
            return {
                "success": False,
                "error": f"未知 action: '{action}'。可用值：outline, detail, quiz, explain, progress",
            }

    except Exception as e:
        return {"success": False, "response": "", "error": str(e)}

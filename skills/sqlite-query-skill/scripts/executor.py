"""
SQLite 查询执行器

执行人员信息查询。
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "test.db"


def extract_query_params(user_input: str) -> Dict[str, Any]:
    """
    从用户输入中提取查询参数

    Args:
        user_input: 用户输入的自然语言

    Returns:
        查询参数字典
    """
    params = {
        "query_type": "list_all",
        "name": None,
        "department": None,
        "position": None
    }

    # 姓名提取模式
    name_patterns = [
        r"查询?\s*([^\s,，。]{2,4})\s*的?(?:信息|详情|资料)?",
        r"搜索?\s*([^\s,，。]{2,4})",
        r"找(?:一下)?\s*([^\s,，。]{2,4})",
        r"姓([^\s,，。]{1,2})",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, user_input)
        if match:
            name = match.group(1)
            # 过滤掉常见的非姓名词
            if name not in ["所有", "全部", "员工", "同事", "人员", "信息", "详情"]:
                params["name"] = name
                params["query_type"] = "search_person"
                break

    # 部门提取模式
    dept_patterns = [
        r"([^\s,，。]{2,10})部(?:门)?(?:的)?(?:员工|同事|人员)",
        r"部门[:：\s]*([^\s,，。]{2,10})",
    ]

    for pattern in dept_patterns:
        match = re.search(pattern, user_input)
        if match:
            dept = match.group(1)
            if dept not in ["所有", "全部"]:
                params["department"] = dept
                params["query_type"] = "search_department"
                break

    # 职位提取模式
    position_patterns = [
        r"([^\s,，。]{2,10})(?:工程师|经理|主管|专员|总监|设计师)",
        r"职位[:：\s]*([^\s,，。]{2,10})",
    ]

    for pattern in position_patterns:
        match = re.search(pattern, user_input)
        if match:
            params["position"] = match.group(1)
            params["query_type"] = "search_position"
            break

    return params


def build_sql_query(params: Dict[str, Any]) -> tuple:
    """
    构建 SQL 查询语句

    Args:
        params: 查询参数

    Returns:
        (SQL 语句, 参数元组)
    """
    base_sql = "SELECT * FROM persons WHERE 1=1"
    conditions = []
    sql_params = []

    if params.get("name"):
        conditions.append("name LIKE ?")
        sql_params.append(f"%{params['name']}%")

    if params.get("department"):
        conditions.append("department LIKE ?")
        sql_params.append(f"%{params['department']}%")

    if params.get("position"):
        conditions.append("position LIKE ?")
        sql_params.append(f"%{params['position']}%")

    if conditions:
        sql = base_sql + " AND " + " AND ".join(conditions)
    else:
        sql = base_sql

    sql += " LIMIT 10"

    return sql, tuple(sql_params)


def format_result(row: tuple) -> Dict[str, Any]:
    """
    格式化查询结果

    Args:
        row: 数据库行

    Returns:
        格式化的字典
    """
    return {
        "id": row[0],
        "name": row[1],
        "department": row[2],
        "position": row[3],
        "email": row[4],
        "phone": row[5],
        "hire_date": row[6]
    }


def execute(context: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行 SQLite 查询

    Args:
        context: 执行上下文
        input_data: 输入数据

    Returns:
        执行结果
    """
    user_input = input_data.get("user_input", "") or context.get("user_input", "")

    # 提取查询参数
    params = extract_query_params(user_input)

    # 检查数据库是否存在
    if not DB_PATH.exists():
        return {
            "success": False,
            "response": "数据库不存在，请先运行 data/init_db.py 初始化数据库。",
            "data": {}
        }

    try:
        # 连接数据库
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # 构建并执行查询
        sql, sql_params = build_sql_query(params)
        cursor.execute(sql, sql_params)

        # 获取结果
        rows = cursor.fetchall()
        results = [format_result(row) for row in rows]

        conn.close()

        # 生成响应
        if not results:
            response = "未找到匹配的人员信息。"
        else:
            response = f"找到 {len(results)} 条记录：\n\n"
            for r in results:
                response += f"**{r['name']}**\n"
                response += f"- 部门: {r['department']}\n"
                response += f"- 职位: {r['position']}\n"
                response += f"- 邮箱: {r['email']}\n"
                response += f"- 电话: {r['phone']}\n"
                response += f"- 入职日期: {r['hire_date']}\n\n"

        return {
            "success": True,
            "response": response,
            "data": {
                "query_type": params["query_type"],
                "results": results,
                "count": len(results)
            }
        }

    except sqlite3.Error as e:
        return {
            "success": False,
            "response": f"数据库查询错误: {str(e)}",
            "data": {"error": str(e)}
        }


# 用于直接测试
if __name__ == "__main__":
    test_inputs = [
        "查询张三的信息",
        "搜索姓李的员工",
        "找一下技术部的同事",
        "列出所有人员"
    ]

    for test_input in test_inputs:
        print(f"\n输入: {test_input}")
        result = execute({"user_input": test_input}, {})
        print(f"结果: {result['response'][:100]}...")

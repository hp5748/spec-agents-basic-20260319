"""
Schema 验证器

提供 JSON Schema 验证功能。
"""

from typing import Any, Dict, List, Optional
import logging

from .types import SchemaDefinition


logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Schema 验证器

    使用 JSON Schema 验证数据格式。

    使用方式:
        validator = SchemaValidator()

        # 验证输入
        schema = {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"]
        }
        is_valid = validator.validate({"order_id": "12345678"}, schema)
    """

    def __init__(self):
        """初始化验证器"""
        self._jsonschema = None
        self._load_jsonschema()

    def _load_jsonschema(self) -> bool:
        """加载 jsonschema 库"""
        try:
            import jsonschema
            self._jsonschema = jsonschema
            return True
        except ImportError:
            logger.warning("jsonschema 库未安装，Schema 验证将被跳过")
            return False

    @property
    def available(self) -> bool:
        """检查验证器是否可用"""
        return self._jsonschema is not None

    def validate(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """
        验证数据是否符合 Schema

        Args:
            data: 待验证数据
            schema: JSON Schema 定义

        Returns:
            bool: 验证是否通过
        """
        if not self.available:
            logger.debug("jsonschema 不可用，跳过验证")
            return True

        try:
            self._jsonschema.validate(instance=data, schema=schema)
            return True
        except self._jsonschema.ValidationError as e:
            logger.warning(f"Schema 验证失败: {e.message}")
            return False
        except self._jsonschema.SchemaError as e:
            logger.error(f"Schema 定义错误: {e.message}")
            return False

    def validate_with_errors(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> tuple:
        """
        验证数据并返回详细错误信息

        Args:
            data: 待验证数据
            schema: JSON Schema 定义

        Returns:
            tuple: (是否通过, 错误列表)
        """
        if not self.available:
            return True, []

        errors = []
        try:
            self._jsonschema.validate(instance=data, schema=schema)
            return True, []
        except self._jsonschema.ValidationError as e:
            errors.append({
                "path": list(e.absolute_path),
                "message": e.message,
                "validator": e.validator,
            })
            return False, errors
        except self._jsonschema.SchemaError as e:
            errors.append({
                "path": [],
                "message": f"Schema 错误: {e.message}",
                "validator": "schema",
            })
            return False, errors

    def validate_schema_definition(
        self,
        definition: SchemaDefinition,
        data: Dict[str, Any]
    ) -> bool:
        """
        使用 SchemaDefinition 验证数据

        Args:
            definition: Schema 定义
            data: 待验证数据

        Returns:
            bool: 验证是否通过
        """
        # 检查必填字段
        for field in definition.required:
            if field not in data:
                logger.warning(f"缺少必填字段: {field}")
                return False

        # 使用 JSON Schema 验证
        return self.validate(data, definition.schema)


# 全局验证器实例
_validator: Optional[SchemaValidator] = None


def get_validator() -> SchemaValidator:
    """获取全局验证器实例"""
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator


def validate(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    快捷验证函数

    Args:
        data: 待验证数据
        schema: JSON Schema 定义

    Returns:
        bool: 验证是否通过
    """
    return get_validator().validate(data, schema)

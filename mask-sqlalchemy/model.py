# !/usr/local/python/bin/python
# -*- coding: utf-8 -*-
# (C) Wu Dong, 2021
# All rights reserved
# @Author: 'Wu Dong <wudong@eastwu.cn>'
# @Time: '6/29/21 10:50 AM'
# sys
import re
# 3p
import sqlalchemy
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.schema import _get_table_key


def should_set_tablename(cls):
    if cls.__dict__.get("__abstract__", False) or not any(isinstance(b, DeclarativeMeta) for b in cls.__mro__[1:]):
        return False

    for base in cls.__mro__:
        if "__tablename__" not in base.__dict__:
            continue

        if isinstance(base.__dict__["__tablename__"], declared_attr):
            return False

        return not (
            base is cls
            or base.__dict__.get("__abstract__", False)
            or not isinstance(base, DeclarativeMeta)
        )

    return True


def camel_to_snake_case(name):
    """ 将驼峰命名规则，修改成下划线规则
    """
    name = re.sub(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))", r"_\1", name)
    return name.lower().lstrip("_")


class NameMetaMixin(type):

    def __init__(cls, name, bases, d):
        if should_set_tablename(cls):
            cls.__tablename__ = camel_to_snake_case(cls.__name__)

        super().__init__(name, bases, d)

        if (
            "__tablename__" not in cls.__dict__
            and "__table__" in cls.__dict__
            and cls.__dict__["__table__"] is None
        ):
            del cls.__table__

    def __table_cls__(cls, *args, **kwargs):
        key = _get_table_key(args[0], kwargs.get("schema"))

        if key in cls.metadata.tables:
            return sqlalchemy.Table(*args, **kwargs)

        for arg in args:
            if (isinstance(arg, sqlalchemy.Column) and arg.primary_key) or isinstance(
                arg, sqlalchemy.PrimaryKeyConstraint
            ):
                return sqlalchemy.Table(*args, **kwargs)

        for base in cls.__mro__[1:-1]:
            if "__table__" in base.__dict__:
                break
        else:
            return sqlalchemy.Table(*args, **kwargs)

        if "__tablename__" in cls.__dict__:
            del cls.__tablename__


class BindMetaMixin(type):
    """ 实现将 __bind__key__ 转换成实际SQLAlchemy使用的 bind_key
    """

    def __init__(cls, name, bases, d):
        bind_key = d.pop("__bind_key__", None) or getattr(cls, "__bind_key__", None)
        super().__init__(name, bases, d)

        if bind_key is not None and getattr(cls, "__table__", None) is not None:
            cls.__table__.info["bind_key"] = bind_key


class DefaultMeta(NameMetaMixin, BindMetaMixin, DeclarativeMeta):

    pass


class Model:

    # 查询的类，默认值为 sqalchemy.orm.Query
    # 实际调用时进行初始化
    query_class = None

    # Query包装类，重写 __get__ 方法，自动生成 Query 实例
    query = None

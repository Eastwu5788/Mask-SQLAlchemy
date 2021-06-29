# !/usr/local/python/bin/python
# -*- coding: utf-8 -*-
# (C) Wu Dong, 2021
# All rights reserved
# @Author: 'Wu Dong <wudong@eastwu.cn>'
# @Time: '6/29/21 10:49 AM'
# sys
import typing as t
from threading import Lock
from threading import get_ident
# 3p
import sqlalchemy
from sqlalchemy import (
    orm,
    schema,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    declarative_base,
    DeclarativeMeta,
    Session as SessionBase
)
# project
from mask.globals import current_app
from .model import (
    DefaultMeta,
    Model
)
if t.TYPE_CHECKING:
    from mask import Mask


__version__ = "1.0.0a1"


class BindSession(SessionBase):

    def __init__(self, db, autocommit=False, autoflush=True, **options):
        """ 此Session可以根据binds映射关系，自动找到响应的engine
        """
        self.db = db
        self.app = db.get_app()

        bind = options.pop("bind", None) or db.engine
        binds = options.pop("binds", db.get_binds(self.app))

        SessionBase.__init__(
            self,
            autocommit=autocommit,
            autoflush=autoflush,
            bind=bind,
            binds=binds,
            **options
        )

    def get_bind(self, mapper=None, **kwargs):
        """ 根据mapper映射信息找出合适的engine

        :param mapper: Model -> table 映射
        """
        if mapper is not None:
            # SQLAlchemy >= 1.3 版本才有
            persist_selectable = mapper.persist_selectable

            # 读取 bind_key
            info = getattr(persist_selectable, "info", {})
            bind_key = info.get("bind_key")
            if bind_key is not None:
                # 读取预先格式化好的engine，创建 _EngineConnector 实例
                return self.db.get_engine(self.app, bind=bind_key)
        # 默认调用父类 get_bind 方法
        return super().get_bind(mapper, **kwargs)


class _EngineConnector:

    def __init__(self, sa, app, bind=None):
        """ 初始化engine连接器，一个数据库对应一个Connector
        """
        self._sa = sa
        self._app = app
        self._engine = None
        self._bind = bind
        self._connect_for = None
        self._lock = Lock()

    def get_uri(self):
        """ 获取当前bind的uri
        """
        # 默认去除对单数据库的连接方式
        if self._bind is None:
            return None

        # 多个数据库绑定时的处理
        binds = self._app.config.get("SQLALCHEMY_BINDS") or ()
        if self._bind not in binds:
            raise RuntimeError(f"Bind {self._bind!r} is not configure in 'SQLALCHEMY_BINDS'.")
        return binds[self._bind]

    def get_engine(self):
        with self._lock:
            # 读取数据库连接uri
            uri = self.get_uri()
            if uri == self._connect_for:
                return self._engine

            # 读取，格式化url连接中的配置项并创建真正的engine
            sa_url, options = self.get_options(make_url(uri))
            self._engine = self._sa.create_engine(sa_url, options)
            self._connect_for = uri

        return self._engine

    def dispose(self):
        """ 销毁Engine
        """
        if not self._engine:
            return

        self._engine.dispose()
        # 重置资源
        self._engine = None
        self._connect_for = None

    def get_options(self, sa_url):
        """ 获取所有可选项目
        """
        options = {}
        options.update(self._app.config["SQLALCHEMY_ENGINE_OPTIONS"])
        options.update(self._sa._engine_options)
        return sa_url, options


class _QueryProperty:

    def __init__(self, sa):
        self.sa = sa

    def __get__(self, obj, cls):  # pylint: disable=inconsistent-return-statements
        try:
            mapper = orm.class_mapper(cls)
            if mapper:
                return cls.query_class(mapper, session=self.sa.session())
        except orm.exc.UnmappedClassError:
            return None


def _include_sqlalchemy(obj, _):
    """ 将原生SQLAlchemy的模块注册到Glib SQLAlchemy 中
    """
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))


class SQLAlchemy:

    Query = None

    def __init__(
            self,
            app: t.Optional["Mask"] = None,
            session_options: t.Optional[dict] = None,
            metadata: t.Optional["schema.MetaData"] = None,
            query_class: t.Optional["orm.Query"] = orm.Query,
            model_class: t.Optional["Model"] = Model,
            engine_options: t.Optional[dict] = None,
    ) -> None:
        """ 创建一个SQLAlchemy用于替代原始的类型
        """
        self.app = app

        self.Query = query_class
        self.session = self.create_scoped_session(session_options)
        self.Model = self.make_declarative_base(model_class, metadata)
        self._engine_lock = Lock()
        self._engine_options = engine_options or {}
        self.connectors = {}

        _include_sqlalchemy(self, query_class)

        if app is not None:
            self.init_app(app)

    @property
    def engine(self):
        """ 构造属性，创建engine
        """
        return self.get_engine()

    def get_engine(self, app: t.Optional["Mask"] = None, bind: str = None):
        """ 依据bind创建一个engine
        """
        app = self.get_app(app)

        with self._engine_lock:
            connector = self.connectors.get(bind)
            if connector is None:
                connector = _EngineConnector(self, self.get_app(app), bind)
                self.connectors[bind] = connector

            return connector.get_engine()

    def _dispose_all_engine(self):
        """ 运行时更新配置时，账号密码有可能会发生变化，所以需要销毁所有数据库连接

        TIPS: 此操作会导致正在运行的请求失败
        """
        with self._engine_lock:
            for _, connector in self.connectors.items():
                connector.dispose()
            self.connectors.clear()

    def create_engine(self, sa_url, engine_opts):
        """ 创建engine

        :param sa_url: 格式化后的url
        :param engine_opts: 连接参数
        """
        return sqlalchemy.create_engine(sa_url, **engine_opts)

    def create_scoped_session(self, options=None):
        """ 创建session
        """
        options = options or {}

        scope_func = options.pop("scopefunc", get_ident)
        options.setdefault("query_cls", self.Query)
        return orm.scoped_session(self.create_session(options), scopefunc=scope_func)

    def create_session(self, options):
        """ 创建session
        """
        return orm.sessionmaker(class_=BindSession, db=self, **options)

    def make_declarative_base(self, model, matadata=None):
        """ 利用 SQAlchemy 工厂函数，创建模型基类

        :param model: 用户定义模型基类，或者实例
        :param matadata: 元数据，状态所有表结构
        """
        if not isinstance(model, DeclarativeMeta):
            model = declarative_base(cls=model, name="Model", metadata=matadata, metaclass=DefaultMeta)

        if not getattr(model, "query_class", None):
            model.query_class = self.Query

        model.query = _QueryProperty(self)
        return model

    def get_binds(self, app=None):
        """ 获取当前的所有binds
        """
        app = self.get_app(app)
        binds = [None] + list(app.config.get("SQLALCHEMY_BINDS") or ())
        ret_val = {}
        for bind in binds:
            engine = self.get_engine(app, bind)
            tables = self.get_tables_for_bind(bind)
            ret_val.update({table: engine for table in tables})
        return ret_val

    def init_app(self, app):
        """ glib扩展形式，初始化SQLAlchemy扩展
        """
        # TODO: 从线程池有拉取app
        self.app = app

        app.config.setdefault("SQLALCHEMY_BINDS", None)
        app.config.setdefault("SQLALCHEMY_COMMIT_ON_TEARDOWN", False)
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})

        # 如果配置更新，需要重新释放所有旧的链接
        # 适用于配置运行时动态更新的情况
        self._dispose_all_engine()

        app.extensions["SQLAlchemy"] = self

        @app.teardown_appcontext
        def shutdown_session(exc):  # pylint: disable=unused-variable
            """ Shutdown session when error
            """
            self.session.remove()
            return exc

    def get_app(self, reference_app=None):
        """ 获取当前的Application
        """
        if reference_app is not None:
            return reference_app

        # 查找当前的APP
        if current_app:
            return current_app._get_current_object()

        if self.app is not None:
            return self.app

        raise RuntimeError(
            "No application fund."
        )

    def get_tables_for_bind(self, bind=None):
        """ 查询绑定的数据库下面的所有表
        """
        result = []
        for table in self.Model.metadata.tables.values():
            if table.info.get("bind_key") == bind:
                result.append(table)
        return result

# !/usr/local/python/bin/python
# -*- coding: utf-8 -*-
# (C) Wu Dong, 2021
# All rights reserved
# @Author: 'Wu Dong <wudong@eastwu.cn>'
# @Time: '6/29/21 2:55 PM'
from mask import Mask
from examples.protos.hello_pb2 import HelloRequest, HelloResponse
from mask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column,
    Integer,
    String
)


app = Mask(__name__)

db = SQLAlchemy()
db.init_app(app)


class UserInfoModel(db.Model):

    __bind_key__ = "test_db"
    __tablename__ = "test_user_info"

    id = Column(Integer, default=0, primary_key=True, nullable=False, comment="自增ID")
    user_name = Column(String, default="", nullable=False, comment="用户名称")
    user_desc = Column(String, default="", nullable=False, comment="用户描述信息")


@app.route(method="SayHello", service="Hello")
def say_hello_handler(request: HelloRequest) -> HelloResponse:
    desc = UserInfoModel.query.filter(UserInfoModel.user_name == request.name).first()
    return HelloResponse(message=desc.user_desc)


if __name__ == "__main__":
    app.run(port=10086)

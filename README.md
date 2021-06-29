## Mask-SQLAlchemy

`SQLAlchemy` extension for `Mask` .

### Install

`Mask-SQLAlchemy` support pypi packages, you can simply install by:

```
pip install mask-sqlalchemy
```

### Document

`Mask-SQLAlchemy` manual could be found at:  https://mask-sqlalchemy.readthedocs.io/en/latest


### A Simple Example

This is very easy to use `Mask-SQLAlchemy` in your project.

```
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
```

### Configuration

A list of configuration keys currently understood by the extensions:

| Key | Desc |
| ------ | ------- |
| SQLALCHEMY_BINDS | A dictionary that maps bind keys to SQLAlchemy connection URIs. |
| SQLALCHEMY_ENGINE_OPTIONS | A dictionary of keyword args to send to create_engine(). See also engine_options to SQLAlchemy. |


### Coffee

Please give me a cup of coffee, thank you!

BTC: 1657DRJUyfMyz41pdJfpeoNpz23ghMLVM3

ETH: 0xb098600a9a4572a4894dce31471c46f1f290b087

### Links

* Release: https://github.com/Eastwu5788/Mask-SQLAlchemy/releases
* Code: https://github.com/Eastwu5788/Mask-SQLAlchemy
* Issue tracker: https://github.com/Eastwu5788/Mask-SQLAlchemy/issues
* Test status: https://coveralls.io/github/Eastwu5788/Mask-SQLAlchemy

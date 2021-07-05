# !/usr/local/python/bin/python
# -*- coding: utf-8 -*-
# (C) Wu Dong, 2021
# All rights reserved
# @Author: 'Wu Dong <wudong@eastwu.cn>'
# @Time: '6/29/21 10:48 AM'
# sys
from setuptools import setup


setup(
    name="mask-sqlalchemy",
    install_requires=[
        "mask>=1.0.0a1",
        "sqlalchemy>=1.4.20",
    ]
)

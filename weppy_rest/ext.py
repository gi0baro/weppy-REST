# -*- coding: utf-8 -*-
"""
    weppy_rest.ext
    --------------

    Provides REST extension for weppy

    :copyright: (c) 2016 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy.extensions import Extension
from .serializers import Serializer
from .filters import Filter


class REST(Extension):
    default_config = dict(
        default_serializer=Serializer,
        default_filter=Filter,
        page_param='page',
        pagesize_param='page_size',
        min_pagesize=10,
        max_pagesize=25,
        default_pagesize=20,
        base_path='/',
        base_id_path='/<int:rid>'
    )

    def __init__(self, *args, **kwargs):
        super(REST, self).__init__(*args, **kwargs)
        from .appmodule import AppModule
        from .serializers import serialize
        from .filters import filter_params
        self._module = AppModule
        self._serialize = serialize
        self._filter_params = filter_params

    @property
    def module(self):
        return self._module

    @property
    def serialize(self):
        return self._serialize

    @property
    def filter_params(self):
        return self._filter_params

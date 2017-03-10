# -*- coding: utf-8 -*-
"""
    weppy_rest.helpers
    ------------------

    Provides helpers for the REST extension

    :copyright: (c) 2017 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy import response
from weppy.pipeline import Pipe


class SetFetcher(Pipe):
    def __init__(self, mod):
        self.mod = mod

    def pipe(self, next_pipe, **kwargs):
        kwargs['dbset'] = self.mod._fetcher_method()
        return next_pipe(**kwargs)


class RecordFetcher(Pipe):
    def __init__(self, mod):
        self.mod = mod

    def build_error(self):
        response.status = 404
        return self.mod.error_404()

    def pipe(self, next_pipe, **kwargs):
        self.fetch_record(kwargs)
        if not kwargs['row']:
            return self.build_error()
        return next_pipe(**kwargs)

    def fetch_record(self, kwargs):
        kwargs['row'] = kwargs['dbset'].where(
            self.mod.model.id == kwargs['rid']
        ).select(self.mod.model.table.ALL).first()
        del kwargs['rid']
        del kwargs['dbset']

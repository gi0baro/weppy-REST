# -*- coding: utf-8 -*-
"""
    weppy_rest.helpers
    ------------------

    Provides helpers for the REST extension

    :copyright: (c) 2016 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy import Handler, response


class SetFetcher(Handler):
    def __init__(self, mod):
        self.mod = mod

    def wrap_call(self, f):
        def wrap(**kwargs):
            kwargs['dbset'] = self.mod._fetcher_method()
            return f(**kwargs)
        return wrap


class RecordFetcher(Handler):
    def __init__(self, mod):
        self.mod = mod

    def build_error(self):
        response.status = 404
        return self.mod.error_404()

    def wrap_call(self, f):
        def wrap(**kwargs):
            self.fetch_record(kwargs)
            if not kwargs['row']:
                return self.build_error()
            return f(**kwargs)
        return wrap

    def fetch_record(self, kwargs):
        kwargs['row'] = kwargs['dbset'].where(
            self.mod.model.id == kwargs['rid']
        ).select(self.mod.model.table.ALL).first()
        del kwargs['rid']
        del kwargs['dbset']

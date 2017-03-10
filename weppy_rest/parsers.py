# -*- coding: utf-8 -*-
"""
    weppy_rest.parsers
    ------------------

    Provides REST de-serialization tools

    :copyright: (c) 2017 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy._compat import iteritems
from weppy import request, sdict


class Parser(object):
    attributes = []
    include = []
    exclude = []
    envelope = None

    def __init__(self, model):
        self._model = model
        if not self.attributes:
            self.attributes = []
            writable_map = {}
            for fieldname in self._model.table.fields:
                writable_map[fieldname] = self._model.table[fieldname].writable
            if hasattr(self._model, 'rest_rw'):
                self.attributes = []
                for key, value in iteritems(self._model.rest_rw):
                    if isinstance(value, tuple):
                        writable = tuple[1]
                    else:
                        writable = value
                    writable_map[key] = writable
            for fieldname, writable in iteritems(writable_map):
                if writable:
                    self.attributes.append(fieldname)
            self.attributes += self.include
            for el in self.exclude:
                if el in self.attributes:
                    self.attributes.remove(el)
        _attrs_override_ = []
        for key in dir(self):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_
        self._init()

    def _init(self):
        pass

    def __call__(self, **kwargs):
        return self.__parse_params__(**kwargs)

    def __parse_params__(self, **extras):
        rv = parse_params(*self.attributes, envelope=self.envelope)
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(**extras)
        return rv


def parse_params_with_parser(parser_instance, **extras):
    return parser_instance(**extras)


def parse_params(*accepted_params, **kwargs):
    envelope = kwargs.get('envelope')
    params = request.body_params
    if envelope:
        params = params[envelope]
    rv = sdict()
    for key in accepted_params:
        if key in params:
            rv[key] = params[key]
    return rv

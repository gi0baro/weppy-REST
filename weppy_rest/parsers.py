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
from weppy.utils import cachedprop


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
                        writable = value[1]
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

    @cachedprop
    def _attributes_set(self):
        return set(self.attributes)

    def __parse_params__(self, **extras):
        params = _envelope_filter(request.body_params, self.envelope)
        rv = _parse(self._attributes_set, params)
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(params, **extras)
        return rv


def _envelope_filter(params, envelope=None):
    if not envelope:
        return params
    return params[envelope]


def _parse(accepted_set, params):
    rv = sdict()
    for key in accepted_set & set(params):
        rv[key] = params[key]
    return rv


def parse_params_with_parser(parser_instance, **extras):
    return parser_instance(**extras)


def parse_params(*accepted_params, **kwargs):
    params = _envelope_filter(request.body_params, kwargs.get('envelope'))
    return _parse(set(accepted_params), params)

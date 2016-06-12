# -*- coding: utf-8 -*-

from weppy._compat import iteritems
from weppy import request, sdict


class Filter(object):
    attributes = []
    include = []
    exclude = []
    envelope = None

    def __init__(self, model):
        self._model_ = model
        if not self.attributes:
            if hasattr(self._model_, 'rest_rw'):
                self.attributes = []
                for key, value in iteritems(self._model_.rest_rw):
                    if isinstance(value, tuple):
                        writable = tuple[1]
                    else:
                        writable = value
                    if writable:
                        self.attributes.append(key)
            else:
                self.attributes = [
                    fieldname for fieldname in self._model_.table.fields
                    if self._model_.table[fieldname].writable and
                    self._model_.table[fieldname].type != 'id'
                ]
            self.attributes += self.include
            for el in self.exclude:
                if el in self.attributes:
                    self.attributes.remove(el)
        _attrs_override_ = []
        for key in dir(self):
            if not key.startswith('_') and callable(getattr(self, key)):
                _attrs_override_.append(key)
        self._attrs_override_ = _attrs_override_

    def __call__(self, *args, **kwargs):
        return self.__filter_params__(*args, **kwargs)

    def __filter_params__(self, **extras):
        params = request.body_params
        rv = sdict()
        if self.envelope:
            params = params[self.envelope]
        for key in self.attributes:
            rv[key] = params[key]
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(params)
        return rv


def filter_params(filter_instance):
    return filter_instance()

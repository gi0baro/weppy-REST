# -*- coding: utf-8 -*-

from pydal.objects import Rows
from weppy._compat import iteritems


class Serializer(object):
    attributes = []
    include = []
    exclude = []
    bind_to = None

    def __init__(self, model):
        self._model_ = model
        if not self.attributes:
            if hasattr(self._model_, 'rest_rw'):
                self.attributes = []
                for key, value in iteritems(self._model_.rest_rw):
                    if isinstance(value, tuple):
                        readable = tuple[0]
                    else:
                        readable = value
                    if readable:
                        self.attributes.append(key)
            else:
                self.attributes = [
                    fieldname for fieldname in self._model_.table.fields
                    if self._model_.table[fieldname].readable
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
        return self.__serialize__(*args, **kwargs)

    def __serialize__(self, row, **extras):
        rv = {}
        if self.bind_to:
            row = row[self.bind_to]
        for key in self.attributes:
            rv[key] = row[key]
        for name in self._attrs_override_:
            rv[name] = getattr(self, name)(row, **extras)
        return rv


def serialize(objects, serializer, **extras):
    if objects is None:
        return None
    if not objects:
        return []
    elif not isinstance(objects, (Rows, list, tuple)):
        return serialize([objects], serializer, **extras)[0]
    return [serializer(obj, **extras) for obj in objects]

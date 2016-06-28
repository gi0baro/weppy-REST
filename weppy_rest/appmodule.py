# -*- coding: utf-8 -*-
"""
    weppy_rest.appmodule
    --------------------

    Provides REST AppModule for weppy

    :copyright: (c) 2016 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy import AppModule, sdict, request, response
from weppy.tools import ServiceHandler
from .helpers import SetFetcher, RecordFetcher
from .serializers import serialize as _serialize
from .filters import filter_params as _filter_params, \
    filter_params_with_filter as _filter_params_wfilter


class RESTModule(AppModule):
    def __init__(
        self, app, name, import_name, model, serializer=None, filter=None,
        enabled_methods=['index', 'create', 'read', 'update', 'delete'],
        disabled_methods=[], list_envelope='data', single_envelope=None,
        use_envelope_on_filtering=False, url_prefix=None, hostname=None
    ):
        self._fetcher_method = self._get_dbset
        self.error404 = self.build_error_404
        self.error422 = self.build_error_422
        self._basic_handlers = [ServiceHandler('json')]
        self._common_handlers = []
        super(RESTModule, self).__init__(
            app, name, import_name, url_prefix=url_prefix, hostname=hostname)
        self.ext = self.app.ext.REST
        self._pagination = sdict()
        for key in (
            'page_param', 'pagesize_param', 'min_pagesize', 'max_pagesize',
            'default_pagesize'
        ):
            self._pagination[key] = self.ext.config[key]
        self._path_base = self.ext.config.base_path
        self._path_rid = self.ext.config.base_id_path
        self._serializer_class = serializer or \
            self.ext.config.default_serializer
        self._filter_class = filter or self.ext.config.default_filter
        self._filtering_params_kwargs = {}
        self.model = model
        self.serializer = self._serializer_class(self.model)
        self.filter = self._filter_class(self.model)
        self.enabled_methods = enabled_methods
        self.disabled_methods = disabled_methods
        self.list_envelope = list_envelope
        self.use_envelope_on_filtering = use_envelope_on_filtering
        self.single_envelope = single_envelope
        self.index_handlers = [SetFetcher(self)]
        self.create_handlers = []
        self.read_handlers = [SetFetcher(self), RecordFetcher(self)]
        self.update_handlers = [SetFetcher(self)]
        self.delete_handlers = [SetFetcher(self)]
        self.init()
        self._after_initialize()

    def init(self):
        pass

    def _after_initialize(self):
        self.list_envelope = self.list_envelope or 'data'
        #: adjust single row serialization based on evenlope
        self.serialize_many = self.serialize_with_list_envelope
        self.serialize_one = self.serialize
        if self.single_envelope:
            self.serialize_one = self.serialize_with_single_envelope
            if self.use_envelope_on_filtering:
                self.filter.envelope = self.single_envelope
                self._filtering_params_kwargs = \
                    {'evenlope': self.single_envelope}
        #: adjust enabled methods
        for method_name in self.disabled_methods:
            self.enabled_methods.remove(method_name)
        #: route enabled methods
        self._methods_map = {
            'index': (self._path_base, 'get'),
            'read': (self._path_rid, 'get'),
            'create': (self._path_base, 'post'),
            'update': (self._path_rid, ['put', 'patch']),
            'delete': (self._path_rid, 'delete')
        }
        for key in self.enabled_methods:
            path, methods = self._methods_map[key]
            handlers = getattr(self, key + "_handlers")
            f = getattr(self, "_" + key)
            self.route(path, handlers=handlers, methods=methods, name=key)(f)

    def _remove_default_route(self, method):
        if method not in self.enabled_methods:
            return
        hostname = self.hostname or '__any__'
        name = self.name + "." + method
        for idx, route in enumerate(self.app.route.routes_in[hostname]):
            if route[1].name == name:
                self.app.route.routes_in[hostname] = (
                    self.app.route.routes_in[hostname][:idx] +
                    self.app.route.routes_in[hostname][idx + 1:])
                del self.app.route.routes_out[name]
                break

    @property
    def common_handlers(self):
        return self._common_handlers

    @common_handlers.setter
    def common_handlers(self, handlers):
        self._common_handlers = self._basic_handlers + handlers

    def _get_dbset(self):
        return self.model.all()

    def get_pagination(self):
        try:
            page = int(request.query_params[self._pagination.page_param] or 1)
            assert page > 0
        except:
            page = 1
        try:
            page_size = int(
                request.query_params[self._pagination.pagesize_param] or 20)
            assert (
                self._pagination.min_pagesize <= page_size <=
                self._pagination.max_pagesize)
        except:
            page_size = self._pagination.default_pagesize
        return page, page_size

    def build_error_404(self):
        return {'errors': {'id': 'record not found'}}

    def build_error_422(self, errors=None):
        if errors:
            return {'errors': errors.as_dict()}
        return {'errors': {'request': 'unprocessable entity'}}

    def serialize(self, data):
        return _serialize(data, self.serializer)

    def serialize_with_list_envelope(self, data):
        return {self.list_envelope: self.serialize(data)}

    def serialize_with_single_envelope(self, data):
        return {self.single_envelope: self.serialize(data)}

    def filter_params(self, *params):
        if params:
            return _filter_params(*params, **self._filtering_params_kwargs)
        return _filter_params_wfilter(self.filter)

    #: default routes
    def _index(self, dbset):
        rows = dbset.select(
            self.model.table.ALL, paginate=self.get_pagination())
        return self.serialize_many(rows)

    def _read(self, row):
        return self.serialize_one(row)

    def _create(self):
        attrs = self.filter_params()
        r = self.model.create(**attrs)
        if r.errors:
            response.status = 422
            return self.error_422(r.errors)
        return self.serialize_one(r.id)

    def _update(self, dbset, rid):
        attrs = self.filter_params()
        r = dbset.where(self.model.id == rid).validate_and_update(**attrs)
        if r.errors:
            response.status = 422
            return self.error_422(r.errors)
        elif not r.updated:
            response.status = 404
            return self.error_404()
        return self.serialize_one(self.model.get(rid))

    def _delete(self, dbset, rid):
        rv = dbset.where(self.model.id == rid).delete()
        if not rv:
            response.status = 404
            return self.error_404()
        return {}

    #: decorators
    def get_dbset(self, f):
        self._fetcher_method = f
        return f

    def index(self, handlers=[]):
        self._remove_default_route('index')
        handlers = self.index_handlers + handlers
        return self.route(self._path_base, handlers=handlers, methods='get')

    def read(self, handlers=[]):
        self._remove_default_route('read')
        handlers = self.read_handlers + handlers
        return self.route(self._path_rid, handlers=handlers, methods='get')

    def create(self, handlers=[]):
        self._remove_default_route('create')
        handlers = self.create_handlers + handlers
        return self.route(self._path_base, handlers=handlers, methods='post')

    def update(self, handlers=[]):
        self._remove_default_route('update')
        handlers = self.update_handlers + handlers
        return self.route(
            self._path_rid, handlers=handlers, methods=['put', 'patch'])

    def delete(self, handlers=[]):
        self._remove_default_route('delete')
        handlers = self.delete_handlers + handlers
        return self.route(self._path_rid, handlers=handlers, methods='delete')

    def on_404(self, f):
        self.error_404 = f
        return f

    def on_422(self, f):
        self.error_422 = f
        return f

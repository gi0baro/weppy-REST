# -*- coding: utf-8 -*-
"""
    weppy_rest.appmodule
    --------------------

    Provides REST AppModule for weppy

    :copyright: (c) 2017 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy import AppModule, sdict, request, response
from weppy.tools import ServicePipe
from .helpers import SetFetcher, RecordFetcher
from .serializers import serialize as _serialize
from .parsers import (
    parse_params as _parse_params,
    parse_params_with_parser as _parse_params_wparser)


class RESTModule(AppModule):
    @classmethod
    def from_app(
        cls, app, import_name, name, model, serializer, parser,
        enabled_methods, disabled_methods, list_envelope, single_envelope,
        use_envelope_on_parsing, url_prefix, hostname
    ):
        return cls(
            app, name, import_name, model, serializer, parser,
            enabled_methods, disabled_methods, list_envelope, single_envelope,
            use_envelope_on_parsing, url_prefix, hostname
        )

    @classmethod
    def from_module(
        cls, mod, import_name, name, model, serializer, parser,
        enabled_methods, disabled_methods, list_envelope, single_envelope,
        use_envelope_on_parsing, url_prefix, hostname
    ):
        if '.' in name:
            raise RuntimeError(
                "Nested app modules' names should not contains dots"
            )
        name = mod.name + '.' + name
        if url_prefix and not url_prefix.startswith('/'):
            url_prefix = '/' + url_prefix
        module_url_prefix = (mod.url_prefix + (url_prefix or '')) \
            if mod.url_prefix else url_prefix
        hostname = hostname or mod.hostname
        return cls(
            mod.app, name, import_name, model, serializer, parser,
            enabled_methods, disabled_methods, list_envelope, single_envelope,
            use_envelope_on_parsing, module_url_prefix, hostname, mod.pipeline
        )

    def __init__(
        self, app, name, import_name, model, serializer=None, parser=None,
        enabled_methods=['index', 'create', 'read', 'update', 'delete'],
        disabled_methods=[], list_envelope='data', single_envelope=None,
        use_envelope_on_parsing=False, url_prefix=None, hostname=None,
        pipeline=[]
    ):
        self._fetcher_method = self._get_dbset
        self.error_404 = self.build_error_404
        self.error_422 = self.build_error_422
        add_service_pipe = True
        super_pipeline = list(pipeline)
        for pipe in super_pipeline:
            if isinstance(pipe, ServicePipe):
                add_service_pipe = False
                break
        if add_service_pipe:
            super_pipeline.insert(0, ServicePipe('json'))
        super(RESTModule, self).__init__(
            app, name, import_name, url_prefix=url_prefix, hostname=hostname,
            pipeline=super_pipeline)
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
        self._parser_class = parser or self.ext.config.default_parser
        self._parsing_params_kwargs = {}
        self.model = model
        self.serializer = self._serializer_class(self.model)
        self.parser = self._parser_class(self.model)
        self.enabled_methods = enabled_methods
        self.disabled_methods = disabled_methods
        self.list_envelope = list_envelope
        self.use_envelope_on_parsing = use_envelope_on_parsing
        self.single_envelope = single_envelope
        self.index_pipeline = [SetFetcher(self)]
        self.create_pipeline = []
        self.read_pipeline = [SetFetcher(self), RecordFetcher(self)]
        self.update_pipeline = [SetFetcher(self)]
        self.delete_pipeline = [SetFetcher(self)]
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
            if self.use_envelope_on_parsing:
                self.parser.envelope = self.single_envelope
                self._parsing_params_kwargs = \
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
            pipeline = getattr(self, key + "_pipeline")
            f = getattr(self, "_" + key)
            self.route(path, pipeline=pipeline, methods=methods, name=key)(f)

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

    def serialize(self, data, **extras):
        return _serialize(data, self.serializer, **extras)

    def serialize_with_list_envelope(self, data, **extras):
        return {self.list_envelope: self.serialize(data, **extras)}

    def serialize_with_single_envelope(self, data, **extras):
        return {self.single_envelope: self.serialize(data, **extras)}

    def parse_params(self, *params):
        if params:
            return _parse_params(*params, **self._parsing_params_kwargs)
        return _parse_params_wparser(self.parser)

    #: default routes
    def _index(self, dbset):
        rows = dbset.select(
            self.model.table.ALL, paginate=self.get_pagination())
        return self.serialize_many(rows)

    def _read(self, row):
        return self.serialize_one(row)

    def _create(self):
        response.status = 201
        attrs = self.parse_params()
        r = self.model.create(**attrs)
        if r.errors:
            response.status = 422
            return self.error_422(r.errors)
        return self.serialize_one(r.id)

    def _update(self, dbset, rid):
        attrs = self.parse_params()
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

    def index(self, pipeline=[]):
        pipeline = self.index_pipeline + pipeline
        return self.route(
            self._path_base, pipeline=pipeline, methods='get', name='index')

    def read(self, pipeline=[]):
        pipeline = self.read_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods='get', name='read')

    def create(self, pipeline=[]):
        pipeline = self.create_pipeline + pipeline
        return self.route(
            self._path_base, pipeline=pipeline, methods='post', name='create')

    def update(self, pipeline=[]):
        pipeline = self.update_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods=['put', 'patch'],
            name='update')

    def delete(self, pipeline=[]):
        pipeline = self.delete_pipeline + pipeline
        return self.route(
            self._path_rid, pipeline=pipeline, methods='delete', name='delete')

    def on_404(self, f):
        self.error_404 = f
        return f

    def on_422(self, f):
        self.error_422 = f
        return f

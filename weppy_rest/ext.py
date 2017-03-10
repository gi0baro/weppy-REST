# -*- coding: utf-8 -*-
"""
    weppy_rest.ext
    --------------

    Provides REST extension for weppy

    :copyright: (c) 2017 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from weppy.extensions import Extension, listen_signal
from weppy.orm.models import MetaModel
from .appmodule import AppModule, RESTModule
from .serializers import Serializer
from .parsers import Parser


class REST(Extension):
    default_config = dict(
        default_module_class=RESTModule,
        default_serializer=Serializer,
        default_parser=Parser,
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
        from .serializers import serialize
        from .parsers import parse_params
        self._serialize = serialize
        self._parse_params = parse_params

    @listen_signal('before_database')
    def _configure_models_attr(self):
        MetaModel._inheritable_dict_attrs_.append(
            ('rest_rw', {'id': (True, False)}))

    def on_load(self):
        setattr(AppModule, 'rest_module', rest_module_from_module)
        self.app.rest_module = rest_module_from_app

    @property
    def module(self):
        return self.config.default_module_class

    @property
    def serialize(self):
        return self._serialize

    @property
    def parse_params(self):
        return self._parse_params


def rest_module_from_app(
    app, import_name, name, model, serializer=None, parser=None,
    enabled_methods=['index', 'create', 'read', 'update', 'delete'],
    disabled_methods=[], list_envelope='data', single_envelope=None,
    use_envelope_on_parsing=False, url_prefix=None, hostname=None,
    module_class=None
):
    module_class = module_class or app.ext.REST.config.default_module_class
    return module_class.from_app(
        app, import_name, name, model, serializer, parser, enabled_methods,
        disabled_methods, list_envelope, single_envelope,
        use_envelope_on_parsing, url_prefix, hostname
    )


def rest_module_from_module(
    mod, import_name, name, model, serializer=None, parser=None,
    enabled_methods=['index', 'create', 'read', 'update', 'delete'],
    disabled_methods=[], list_envelope='data', single_envelope=None,
    use_envelope_on_parsing=False, url_prefix=None, hostname=None,
    module_class=None
):
    module_class = module_class or mod.app.ext.REST.config.default_module_class
    return module_class.from_module(
        mod, import_name, name, model, serializer, parser, enabled_methods,
        disabled_methods, list_envelope, single_envelope,
        use_envelope_on_parsing, url_prefix, hostname
    )

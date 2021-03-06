# weppy-REST

weppy-REST is a REST extension for the [weppy framework](http://weppy.org).

[![pip version](https://img.shields.io/pypi/v/weppy-rest.svg?style=flat)](https://pypi.python.org/pypi/weppy-REST) 

## Installation

You can install weppy-REST using pip:

    pip install weppy-REST

And add it to your weppy application:

```python
from weppy_rest import REST

app.use_extension(REST)
```

## Usage

The weppy-REST extension is intended to be used with weppy models, and it uses application modules to build APIs over them. 

Let's say, for example that you have a task manager app, with a `Task` model like this:

```python
from weppy.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
```

Then, in order to expose REST apis for your `Task` model, you can use the `rest_module` method on your application or on any application module:

```python
from myapp import app, Task

tasks = app.rest_module(__name__, 'api_task', Task, url_prefix='tasks')
```

As you can see, the usage is very similar to the weppy application modules, but we also passed the involved model to the module initialization.

This single line is enough to have a really simple REST api over the `Task` model, since under the default behaviour rest modules will expose 5 different routes:

- an *index* route that will respond to `GET` requests on `/tasks` path listing all the tasks in the database
- a *read* route that will respond to `GET` requests on `/tasks/<int:rid>` path returning a single task corresponding to the record id of the *rid* variable
- a *create* route that will respond to `POST` requests on `/tasks` that will create a new task in the database
- an *update* route that will respond to `PUT` or `PATCH` requests on `/tasks/<int:rid>` that will update the task corresponding to the record id of the *rid* variable
- a *delete* route that will respond to `DELETE` requests on `/tasks/<int:rid>` that will delete the task corresponding to the record id of the *rid* variable.

### REST module parameters

The `rest_module` method accepts several parameters (*bold ones are required*) for its configuration:

| parameter | default | description |
| --- | --- | --- |
| **import_name** | | as for standard modules |
| **name** | | as for standard modules |
| **model** | | the model to use |
| serializer | `None` | a class to be used for serialization |
| parser | `None` | a class to be used for parsing |
| enabled_methods | `str` list: index, create, read, update, delete | the routes that should be enabled on the module |
| disabled_methods | `[]` | the routes that should be disabled on the module |
| list_envelope | `'data'` | the envelope to use on the index route |
| single_envelope | `None` | the envelope to use on all the routes except for index |
| use\_envelope\_on\_parsing | `False` | if set to `True` will use the envelope specified in *single_envelope* option also on parsing |
| url_prefix | `None` | as for standard modules |
| hostname | `None` | as for standard modules |

### Customizing the database set

Under default behavior, any REST module will use `Model.all()` as the database set on every operation.

When you need to customize it, you can use the `get_dbset` decorator. 
For example, you may gonna use the weppy auth module:

```python
from myapp import auth

@tasks.get_dbset
def fetch_tasks():
    return auth.user.tasks
```

or you may have some soft-deletions strategies and want to expose just the records which are not deleted:

```python
@tasks.get_dbset
def fetch_tasks():
    return Task.where(lambda t: t.is_deleted == False)
```

### Customizing routed methods

You can customize every route of the REST module using its `index`, `create`, `read`, `update` and `delete` decorators. In the next examples we'll override the routes with the default ones, in order to show the original code behind the default routes.

```python
from weppy import request

@tasks.index()
def task_list(dbset):
    rows = dbset.select(paginate=tasks.get_pagination())
    return tasks.serialize_many(rows)
```

As you can see, an *index* method should accept the `dbset` parameter, that is injected by the module. This is the default one or the one you defined with the `get_dbset` decorator.

```python
@tasks.read()
def task_single(row):
    return tasks.serialize_one(row)
```

The *read* method should accept the `row` parameter that is injected by the module. Under default behaviour the module won't call your method if it doesn't find the requested record, but instead will return a 404 HTTP response.

```python
@tasks.create()
def task_new():
    attrs = tasks.parse_params()
    resp = Task.create(**attrs)
    if resp.errors:
        response.status = 422
        return tasks.error_422(resp.errors)
    return tasks.serialize_one(resp.id)
```

The *create* method won't need any parameters, and is responsible of creating new records in the database.

```python
@tasks.update()
def task_edit(dbset, rid):
    attrs = tasks.parse_params()
    resp = dbset.where(Task.id == rid).validate_and_update(**attrs)
    if resp.errors:
        response.status = 422
        return tasks.error_422(resp.errors)
    elif not resp.updated:
        response.status = 404
        return tasks.error_404()
    return tasks.serialize_one(Task.get(rid))
```

```python
@tasks.delete()
def task_del(dbset, rid):
    deleted = dbset.where(Task.id == rid).delete()
    if not deleted:
        response.status = 404
        return tasks.error_404()
    return {}
```

The *update* and *delete* methods are quite similar, since they should accept the `dbset` parameter and the `rid` one, which will be the record id requested by the client.

All the decorators accept an additional `pipeline` parameter that you can use to add custom pipes to the routed function:

```python
@tasks.index(pipeline=[MyCustomPipe()])
def task_index:
    # code
```

### Customizing errors

You can define custom methods for the HTTP 404 and 422 errors that will generate the JSON output using the `on_404` and `on_422` decorators:

```python
@tasks.on_404
def task_404err():
    return {'error': 'this is my 404 error'}
    
@tasks.on_422
def task_422err(errors):
    return {'error': 422, 'validation': errors.as_dict()}
```

### Serialization

Under the default behaviour, the REST extension will use the `form_rw` attribute of the involved model, and overwrite the results with the contents of the `rest_rw` attribute if present.

For example, with this model:

```python
from weppy.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    form_rw = {
        'id': False,
        'created_at': False
    }
```

the REST extension will serialize just the *title* and the *is_completed* fields, while with this:

```python
from weppy.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    form_rw = {
        'id': False,
        'created_at': False
    }
    
    rest_rw = {
        'id': True
    }
```

the REST extension will serialize also the *id* field.

#### Serializers

Whenever you need more control over the serialization, you can use the `Serializer` class of the REST extension:

```python
from weppy_rest import Serializer

class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
tasks = app.rest_module(
    __name__, 'api_task', Task, serializer=TaskSerializer, url_prefix='tasks')
```

Serializers are handy when you want to add custom function to serialize something present in your rows. For instance, let's say you have a very simple tagging system:

```python
from weppy.orm import belongs_to, has_many

class Task(Model):
    has_many({'tags': 'TaskTag'})

class TaskTag(Model):
    belongs_to('task')
    name = Field.string()
```

and you want to serialize the tags as an embedded list in your task. Then you just have to add a `tags` method to your serializer:

```python
class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
    def tags(self, row):
        return row.tags().column('name')
```

This is the complete list of rules that the extension will take over serializers:

- `attributes` is read as first step
- the `form_rw` and `rest_rw` attributes of the model are used to fill `attributes` list when this is empty
- the fields in the `include` list will be added to `attributes`
- the fields in the `exclude` list will be removed from `attributes`
- every method defined in the serializer not starting with `_` will be called over serialization and its return value will be added to the JSON object in a key named as the method

You can also use different serialization for the list route and the other ones:

```python
from weppy_rest import Serializer, serialize

class TaskSerializer(Serializer):
    attributes = ['id', 'title']
    
class TaskDetailSerializer(TaskSerializer):
    include = ['is_completed']
    
tasks = app.module(
    __name__, 'api_task', Task, 
    serializer=TaskDetailSerializer, url_prefix='tasks')

@tasks.index()
def task_list(dbset):
    rows = dbset.select(paginate=tasks.get_pagination())
    return serialize(rows, TaskSerializer)
```

> **Note:** under default behaviour the `serialize` method will use the serializer passed to the module.

### Parsing input

Opposite to the serialization, you will have input parsing to parse JSON requests and perform operations on the records.

Under the default behaviour, the REST extension will use the `form_rw` attribute of the involved model, and overwrite the results with the contents of the `rest_rw` attribute if present.

For example, with this model:

```python
from weppy.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    form_rw = {
        'id': False,
        'created_at': False
    }
```

the REST extension will parse the input to allow just the *title* and the *is_completed* fields, while with this:

```python
from weppy.orm import Model, Field

class Task(Model):
    title = Field.string()
    is_completed = Field.bool()
    created_at = Field.datetime()
    
    form_rw = {
        'id': False,
        'created_at': False
    }
    
    rest_rw = {
        'id': (True, False)
        'created_at': True
    }
```

the REST extension will allow also the *created_at* field.

#### Parsers

Very similarly to the `Serializer` class, the extension provides also a `Parser` one:

```python
from weppy_rest import Parser

class TaskParser(Parser):
    attributes = ['title']
    
tasks = app.rest_module(
    __name__, app, 'api_task', Task, parser=TaskParser, url_prefix='tasks')
```

As for serializers, you can define `attributes`, `include` and `exclude` lists in a parser, and add custom methods that will parse the params:

```python
class TaskParser(Parser):
    attributes = ['title']
    
    def created_at(self, params):
        # some code
```

There's also an additional attribute that you can set over a `Parser` which is the `envelope` one, if you expect to have enveloped bodies over `POST`, `PUT` and `PATCH` requests.

### Pagination

REST modules perform pagination over the *index* route under the default behaviour. This is performed with the `paginate` option during the select and the call to the `get_pagination` method:

```python
def get_pagination(self):
    try:
        page = int(request.query_params.page or 1)
        assert page > 0
    except:
        page = 1
    try:
        page_size = int(
            request.query_params.page_size or 20)
        assert (10 <= page_size <= 25)
    except:
        page_size = 20
    return page, page_size
```

You can customize the name of the query params or the default page sizes with the extension configuration, or you can override the method completely with subclassing. 

### Customizing REST modules

#### Extension options

This is the list of all the configuration variables available on the extension for customization – the default values are set:

```python
app.config.REST.default_module_class = RESTModule
app.config.REST.default_serializer = Serializer
app.config.REST.default_parser = Parser
app.config.REST.page_param = 'page'
app.config.REST.pagesize_param = 'page_size'
app.config.REST.min_pagesize = 10
app.config.REST.max_pagesize = 25
app.config.REST.default_pagesize = 20
app.config.REST.base_path = '/'
app.config.REST.base_id_path = '/<int:rid>'
```

This configuration will be used by all the REST modules you create, unless overridden.

#### Subclassing

Under the default behavior, every REST module will use the `RESTModule` class. You can create as many subclasses from this one when you need to apply the same behaviour to several modules:

```python
from weppy_rest import RESTModule

class MyRESTModule(RESTModule):
    def init(self):
        self.disabled_methods = ['delete']
        self.index_pipeline.append(MyCustomPipe())
        self.list_envelope = 'objects'
        self.single_envelope = self.model.__name__.lower()
        
    def _get_dbset(self):
        return self.model.where(lambda m: m.user == session.user.id)
        
    def _index(self, dbset):
        rows = dbset.select(paginate=self.get_pagination())
        rv = self.serialize_many(rows)
        rv['meta'] = {'total': dbset.count()}
        return rv
        
tasks = app.rest_module(
    __name__, app, 'api_task', Task, url_prefix='tasks', 
    module_class=MyRESTModule)
tags = app.rest_module(
    __name__, app, 'api_tag', Tag, url_prefix='tags',
    module_class=MyRESTModule)
```

As you can see, we defined a subclass of the `RESTModule` one and used the `init` method to customize the class initialization for our needs. We **strongly** recommend to use this method and avoid overriding the `__init__` of the class unless you really know what you're doing.

Using the `init` method, we disabled the *delete* route over the module, added a custom pipe over the *index* route and configured the envelope rules.

Here is a list of variables you may want to change inside the `init` method:

- model
- serializer
- parser
- enabled_methods
- disabled_methods
- list_envelope
- single_envelope
- use\_envelope\_on\_parsing

Also, this is the complete list of the pipeline variables and their default values:

```python
def init(self):
    self.index_pipeline = [SetFetcher(self)]
    self.create_pipeline = []
    self.read_pipeline = [SetFetcher(self), RecordFetcher(self)]
    self.update_pipeline = [SetFetcher(self)]
    self.delete_pipeline = [SetFetcher(self)]
```

We've also overridden the methods for the database set retrieval and the *index* route. As you can see, these methods are starting with the `_` since are the default ones and you can still override them with decorators. This is the complete list of methods you may want to override instead of using decorators:

- `_get_dbset`
- `_index`
- `_create`
- `_read`
- `_update`
- `_delete`
- `build_error_404`
- `build_error_422`

There are some other methods you may need to override, like the `get_pagination` one or the serialization ones. Please, check the source code of the `RESTModule` class for further needs.

## License

weppy-REST is released under BSD license. Check the LICENSE file for more details.

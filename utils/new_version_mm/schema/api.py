import pystache

from common.utils import remove_none
from common import mm_param


class ApiBase(object):
    def __init__(self, name):
        self._name = name
        self._path = ""
        self._verb = ""
        self._op_id = ""
        self._msg_prefix = ""
        self._parameters = None

    def render(self):
        v = self._render_data()
        remove_none(v)
        r = [
            pystache.Renderer().render_path(
                "template/resource_api.mustache", v)
        ]

        if self._parameters:
            r.extend(self._generate_parameter_config())

        return r

    def init(self, api_info, all_models, properties):
        api = api_info["api"]
        self._path = api["path"]
        self._verb = api["method"].upper()
        self._op_id = api_info["op_id"]
        self._msg_prefix = api_info.get("msg_prefix", "")

        crud = api_info["crud"]
        if crud.find("c") != -1 or crud.find("u") != -1:
            self._parameters = mm_param.build(
                api_info.get("body", []), all_models)

        if self._parameters:
            self._build_field(properties)

    def _render_data(self):
        return {
            "api_key":   self._name,
            "api_type": "ApiBasic",
            "name":      self._name,
            "path":      self._path,
            "verb":      self._verb,
        }

    def _generate_parameter_config(self):

        def _generate_yaml(params, n):
            r = []
            keys = sorted(params.keys())
            for k in keys:
                v = params[k]
                s = v.to_yaml(n)
                if s:
                    r.extend(s)
            return r

        r = []
        indent = 8
        if self._parameters:
            r.append("%sparameters:\n" % (' ' * indent))
            r.extend(_generate_yaml(self._parameters, indent + 2))

        return r

    def child(self, key):
        if self._msg_prefix == key:
            return self

        if key in self._parameters:
            return self._parameters[key]

        raise Exception("no child with key(%s)" % key)

    def _build_field(self, properties):

        def _find_param(path):
            obj = self
            for k in path.split('.'):
                obj = obj.child(k.strip())

            return obj

        def _set_field(o):
            target = o.path.get(self._op_id)
            if not target:
                return

            path = []
            while o is not None:
                path.append(o.get_item("name"))
                o = o.parent
            path.reverse()

            _find_param(target).set_item("field", ".".join(path))

        for o in properties.values():
            o.parent = None

            o.traverse(_set_field)


class ApiCreate(ApiBase):
    def __init__(self):
        super(ApiCreate, self).__init__("create")

        self._resource_id_path = ""

    def _render_data(self):
        v = super(ApiCreate, self)._render_data()

        v.update({
            "resource_id_path": self._resource_id_path,
            "api_type":         "ApiCreate"
        })
        return v

    def init(self, api_info, all_models, properties):
        super(ApiCreate, self).init(api_info, all_models, properties)

        self._resource_id_path = api_info.get("resource_id_path")


class ApiList(ApiBase):
    def __init__(self):
        super(ApiList, self).__init__("list")

        self._query_params = None
        self._identity = []
        self._msg_prefix = ""

    def _render_data(self):
        v = super(ApiList, self)._render_data()

        v.update({
            "identity": [{"name": i} for i in self._identity],
            "query_params": self._query_params,
            "list_msg_prefix": self._msg_prefix,
            "api_type":         "ApiList"

        })

        return v

    def init(self, api_info, all_models, properties):
        super(ApiList, self).init(api_info, all_models, properties)

        api = api_info["api"]
        self._query_params = [
            {"name": i["name"]} for i in api.get("query_params", {})]
        self._msg_prefix = api_info.get("msg_prefix")


def build_resource_api_config(api_info, all_models, properties):
    r = ["    apis:\n"]

    for k, v in api_info.items():
        t = v.get("type")

        if not t:
            pass
        elif t == "create":
            obj = ApiCreate()
        elif t == "list":
            obj = ApiList()
        else:
            obj = ApiBase(t)

        obj.init(v, all_models, properties)
        r.extend(obj.render())

    return r

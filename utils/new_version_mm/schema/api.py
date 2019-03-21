import pystache

from common.utils import remove_none
from common import mm_param


class ApiBase(object):
    def __init__(self, name):
        self._name = name
        self._path = ""
        self._verb = ""
        self._op_id = ""
        self._parameters = None
        self._async = None
        self.service_type = ""
        self._msg_prefix = ""
        self._msg_prefix_array_items = None

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
        self._msg_prefix = api_info.get("msg_prefix")
        self._msg_prefix_array_items = api_info.get("msg_prefix_array_items")

        crud = api_info["crud"]
        if crud != "" and crud != "r":
            self._parameters = mm_param.build(
                api_info.get("body", []), all_models)

        if self._parameters:
            if not api_info.get("exclude_for_schema"):
                self._build_field(properties)

            v = api_info.get("default_value")
            if v:
                self._set_default_valuse(v)

        ac = api_info.get("async")
        if ac:
            p = ac.get("query_status", {}).get("path_parameter")
            if p:
                r = [{"key": k, "value": v} for k, v in p.items()]
                ac["query_status"]["path_parameter"] = r
                ac["query_status"]["has_path_parameter"] = True

            for k in ["pending", "complete"]:
                p = ac.get("check_status", {}).get(k)
                if p:
                    ac["check_status"][k] = [{"value": v} for v in p]
                    ac["check_status"]["has_" + k] = True

            self._async = ac

    def _render_data(self):
        r = {
            "api_key":   self._name,
            "api_type": "ApiBasic",
            "name":      self._name,
            "path":      self._path,
            "verb":      self._verb,
            "async":     self._async,
            "service_type": self.service_type,
            "msg_prefix": self._msg_prefix
        }

        v = self._msg_prefix_array_items
        if isinstance(v, list) and len(v) > 0:
            r["has_msg_prefix_array_items"] = True

            r["msg_prefix_array_items"] = [
                {"msg_prefix_array_item": i} for i in v]

        return r

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
        if key in self._parameters:
            return self._parameters[key]

        raise Exception("parent:root, no child with key(%s)" % key)

    def _find_param(self, path):
        obj = self
        for k in path.split('.'):
            obj = obj.child(k.strip())

        return obj

    def _build_field(self, properties):

        def _build_index(o):
            path = []
            while o is not None:
                path.append(o.get_item("name"))
                o = o.parent
            path.reverse()
            return ".".join(path)

        r = {}

        def _build_map(o):
            target = o.path.get(self._op_id)
            if not target:
                return

            r[target] = _build_index(o)

        for o in properties.values():
            o.parent = None

            o.traverse(_build_map)

        def _set_field(o):
            o.set_item("field", r.get(_build_index(o)))

        for o in self._parameters.values():
            o.parent = None

            o.traverse(_set_field)

    def _set_default_valuse(self, values):
        for k, v in values.items():
            self._find_param(k).set_item("default", v)


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


class ApiAction(ApiBase):
    def __init__(self):
        super(ApiAction, self).__init__("")

        self._when = ""
        self._path_parameter = None

    def _render_data(self):
        v = super(ApiAction, self)._render_data()
        v["api_type"] = "ApiAction"

        data = {"when": self._when}
        p = self._path_parameter
        if p:
            r = [{"key": k, "value": i} for k, i in p.items()]
            data["path_parameter"] = r
            data["has_path_parameter"] = True

        v["action"] = data
        return v

    def init(self, api_info, all_models, properties):
        super(ApiAction, self).init(api_info, all_models, properties)

        self._name = api_info["op_id"]
        self._when = api_info.get("when")
        self._path_parameter = api_info.get("path_parameter")


class ApiOther(ApiBase):
    def __init__(self):
        super(ApiOther, self).__init__("")

        self._crud = ""

    def _render_data(self):
        v = super(ApiOther, self)._render_data()
        v["api_type"] = "ApiOther"

        v["other"] = {"crud": self._crud}
        return v

    def init(self, api_info, all_models, properties):
        super(ApiOther, self).init(api_info, all_models, properties)

        self._name = api_info["op_id"]
        self._crud = api_info.get("crud")


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


def build_resource_api_config(api_info, all_models, properties,
                              service_type, **kwargs):
    r = ["    apis:\n"]

    for v in api_info.values():
        t = v.get("type")

        obj = None
        if not t:
            if v.get("when"):
                obj = ApiAction()
            else:
                obj = ApiOther()
        elif t == "create":
            obj = ApiCreate()
        elif t == "list":
            obj = ApiList()
        else:
            obj = ApiBase(t)

        obj.init(v, all_models, properties)
        obj.service_type = service_type
        r.extend(obj.render())

    return r

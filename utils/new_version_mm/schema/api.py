import pystache

from common.utils import find_property
from common.utils import remove_none
from common import mm_param


def _build_field(op_id, properties, parameters):

    def _build_index(o):
        path = []
        while o is not None:
            path.append(o.get_item("name"))
            o = o.parent
        path.reverse()
        return ".".join(path)

    r = {}

    def _build_map(o):
        target = o.path.get(op_id)
        if not target:
            return

        r[target] = _build_index(o)

    for o in properties.values():
        o.parent = None

        o.traverse(_build_map)

    def _set_field(o):
        o.set_item("field", r.get(_build_index(o)))

    for o in parameters.values():
        o.parent = None

        o.traverse(_set_field)


class ApiBase(object):
    def __init__(self, name):
        self._name = name
        self._path = ""
        self._verb = ""
        self._parameters = None
        self._async = None
        self.service_type = ""
        self._msg_prefix = ""
        self._msg_prefix_array_items = None
        self._render_parameters = True
        self._has_response = False

    def render(self):
        v = self._render_data()
        remove_none(v)
        r = [
            pystache.Renderer().render_path(
                "template/resource_api.mustache", v)
        ]

        if self._render_parameters:
            c = self._generate_parameter_config()
            if c:
                r.extend(c)

        return r

    def init(self, api_info, all_models, properties):
        api = api_info["api"]
        self._path = api["path"]
        self._verb = api["method"].upper()
        self._msg_prefix = api_info.get("msg_prefix")
        self._msg_prefix_array_items = api_info.get("msg_prefix_array_items")
        self._has_response = (
            api.get("response", {}).get("datatype") in all_models)

        self._build_async_info(api_info)

        body = api_info.get("body")
        if body and isinstance(body, list):
            self._parameters = mm_param.build(body, all_models)

            if not api_info.get("exclude_for_schema"):
                _build_field(api_info["op_id"], properties, self._parameters)

            self._exe_special_cmds(api_info)

    def _exe_special_cmds(self, api_info):
        cmds = api_info.get("special_cmds", {})
        if not cmds:
            return

        dv = cmds.get("set_value")
        if isinstance(dv, dict):
            for k, v in dv.items():
                find_property(self._parameters, k).set_item("default", v)

        dv = cmds.get("depends_on")
        if isinstance(dv, dict):
            for k, v in dv.items():
                p = find_property(self._parameters, k)
                p.set_item("field", p.parent.child(v).get_item("field"))

    def _build_async_info(self, api_info):
        ac = api_info.get("async")
        if ac and isinstance(ac, dict):

            qs = ac.get("query_status")
            if qs and isinstance(qs, dict):

                p = qs.get("path_parameter")
                if p and isinstance(p, dict):
                    r = [{"key": k, "value": v} for k, v in p.items()]
                    ac["query_status"]["path_parameter"] = r
                    ac["query_status"]["has_path_parameter"] = True

                if "service_type" not in qs:
                    qs["service_type"] = self.service_type

                if "name" not in qs:
                    qs["name"] = self._name + "_async"

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
            "msg_prefix": self._msg_prefix,
            "has_response": str(self._has_response).lower(),
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
        self._name = api_info["op_id"]
        self._when = api_info.get("when")
        self._path_parameter = api_info.get("path_parameter")

        # super.init will use self._name
        super(ApiAction, self).init(api_info, all_models, properties)


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
        self._name = api_info["op_id"]
        self._crud = api_info.get("crud")

        # super.init will use self._name
        super(ApiOther, self).init(api_info, all_models, properties)


class ApiList(ApiBase):
    def __init__(self, read_api):
        super(ApiList, self).__init__("list")

        self._query_params = None
        self._identity = None
        self._resource_id_path = ""

        self._read_api = read_api

    def _render_data(self):
        v = super(ApiList, self)._render_data()

        v.update({
            "api_type": "ApiList",
            "identity": [
                {"name": i, "ref": j} for i, j in self._identity.items()],
            "has_identity":     True,
            "query_params":     self._query_params,
            "has_query_params": len(self._query_params) > 0,
            "resource_id_path": self._resource_id_path,
        })

        return v

    def init(self, api_info, all_models, properties):
        super(ApiList, self).init(api_info, all_models, properties)

        v = {i: self._parameters[i] for i in api_info["identity"]}
        if self._read_api:
            _build_field(self._read_api["op_id"], properties, v)
        elif api_info.get("exclude_for_schema"):
            raise Exception("can't build field for identity of list api")

        self._identity = {k: i.get_item("field") for k, i in v.items()}

        v = ["marker", "offset", "limit", "start"]
        for i in self._identity:
            v.append(i)

        self._query_params = [
            {"name": i["name"]}
            for i in api_info["api"].get("query_params", []) if i["name"] in v
        ]

        self._render_parameters = (not self._read_api)

        self._resource_id_path = api_info.get("resource_id_path")


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
            obj = ApiList(api_info.get("read"))
        else:
            obj = ApiBase(t)

        # obj.init will use obj.service_type
        obj.service_type = service_type
        obj.init(v, all_models, properties)
        r.extend(obj.render())

    return r

import pystache

from common.utils import build_path


class _Resource(object):
    def __init__(self, name, service_type, parameter, properties, identity):
        self._name = name
        self._service_type = service_type
        self._paths = {}
        self._msg_prefix = {}
        self._description = ""
        self._create_verb = ""
        self._update_verb = ""
        self._list_op = ListOp(identity)
        self._parameters = parameter
        self._properties = properties

    def render(self):
        v = {
            "name": self._name,
            "service_type": self._service_type,
            "paths": self._paths,
            "msg_prefix": self._msg_prefix,
            "description": self._description,
            "create_verb": self._create_verb,
            "update_verb": self._update_verb,
            "list_info": self._list_op.to_map()
        }
        for k in v.keys():
            if not v[k]:
                v.pop(k)

        r = [
            pystache.Renderer().render_path("template/resource.mustache", v)
        ]
        r.extend(self._generate_parameter_config())
        return r

    def init(self, api_info, tag_info):
        for k, v in api_info.items():
            if k == "list":
                continue

            s = v.get("msg_prefix", None)
            if s:
                self._msg_prefix[k] = s

            self._paths[k] = v["api"]["path"]

        self._create_verb = api_info["create"]["create_verb"]

        self._update_verb = api_info.get("update", {}).get("update_verb")

        self._description = tag_info.get("description", "")

        if "list" in api_info:
            self._list_op.init(api_info["list"])

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
        indent = 4
        if self._parameters:
            r.append("%sparameters:\n" % (' ' * indent))
            r.extend(_generate_yaml(self._parameters, indent + 2))

        r.append("%sproperties:\n" % (' ' * indent))
        r.extend(_generate_yaml(self._properties, indent + 2))
        return r


class ListOp(object):
    def __init__(self, identity):
        self._path = ""
        self._query_params = None
        self._identity = identity
        self._msg_prefix = ""

    def init(self, api_info):
        api = api_info["api"]

        self._path = build_path(api["path"])
        self._query_params = [{"name": i["name"]} for i in api["query_params"]]
        self._msg_prefix = api_info.get("msg_prefix")

    def to_map(self):
        v = {
            "path": self._path,
            "identity": [{"name": i} for i in self._identity],
            "query_params": self._query_params,
            "list_msg_prefix": self._msg_prefix
        }
        for k in v.keys():
            if not v[k]:
                v.pop(k)

        return v


def _set_output(properties):
    def _output(n):
        p = n.parent
        if n.get_item("crud") == 'r' and (
                p is None or p.get_item("crud") != 'r'):
            n.set_item("output", True)

    for v in properties.values():
        v.parent = None
        v.traverse(_output)


def get_resource_name(tag_info, custom_configs):
    rn = tag_info["name"]
    if custom_configs:
        rn = custom_configs.get("resource_name", rn)

    if isinstance(rn, unicode):
        raise Exception("Must config resouce_name in English, "
                        "because the tag is Chinese")

    return rn


def build_resource_config(api_info, properties, tag_info,
                          custom_configs, service_type):
    rn = get_resource_name(tag_info, custom_configs)

    identity = custom_configs.get("identity")
    if not identity:
        raise Exception("Must config identity to verify the rsource")

    params = {}
    pros = {}
    for k, v in properties.items():
        if "r" in v.get_item("crud"):
            pros[k] = v

        else:
            params[k] = v

    _set_output(pros)

    v = set(identity) - set([v.get_item("name") for v in pros.values()])
    if v:
        raise Exception("Not all items(%s) of identity are in "
                        "resource's properties" % ", ".joint(v))

    rid = custom_configs.get("resource_id")
    if rid:
        if rid not in pros:
            raise Exception("Can't find the property(%s) in properties" % rid)

        pros[rid].set_item("is_id", True)

    resource = _Resource(rn, service_type, params, pros, identity)

    resource.init(api_info, tag_info)

    return resource.render()

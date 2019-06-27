import pystache

from common.utils import remove_none


class _Resource(object):
    def __init__(self, name, desc, properties, parameter=None):
        self._name = name
        self._description = desc
        self.version = ""
        self._parameters = parameter
        self._properties = properties

    def render(self):
        v = {
            "name": self._name,
            "description": self._description,
            "version": self.version,
        }
        remove_none(v)

        r = [
            pystache.Renderer().render_path("template/resource.mustache", v)
        ]
        r.extend(self._generate_parameter_config())
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
        indent = 4
        if self._parameters:
            r.append("%sparameters:\n" % (' ' * indent))
            r.extend(_generate_yaml(self._parameters, indent + 2))

        r.append("%sproperties:\n" % (' ' * indent))
        r.extend(_generate_yaml(self._properties, indent + 2))
        return r


def _set_output(properties):
    def _output(n):
        p = n.parent
        if n.get_item("crud") == 'r' and (
                p is None or p.get_item("crud") != 'r'):
            n.set_item("output", True)

    for v in properties.values():
        v.parent = None
        v.traverse(_output)


def _set_attributes(api_info, properties):
    info = {v["op_id"]: v["crud"] for v in api_info.values()}
    read_apis = {
        v["op_id"]: v["op_id"] if v.get("type") is None else v["type"]
        for v in api_info.values() if v["crud"].find("r") != -1
    }

    def _set_crud(n, leaf):
        m = {"c": 0, "r": 0, "u": 0, "d": 0}

        if leaf:
            for v in n.path:
                m[info[v]] += 1

            if m["r"] > 1:
                raise Exception("there are more than one read api have the "
                                "same parameter for property(%s), please "
                                "delete them to leave only "
                                "one" % n.get_item("name"))

        else:
            for i in n.childs():
                for j in i.get_item("crud"):
                    m[j] = 1

        crud = "".join([i for i in "crud" if m[i]])
        if not crud:
            raise Exception("no crud for property(%s)" % n.get_item("name"))

        n.set_item("crud", crud)

    def _set_field(n):
        if n.get_item("crud").find("r") != -1:
            for k, v in n.path.items():
                if info[k] == "r":
                    n.set_item("field", read_apis[k] + "." + v)

    def callbacks(n, leaf):
        _set_crud(n, leaf)
        _set_field(n)

        if n.alias:
            raise Exception(
                "the alias of property(%s) is not empty" % n.get_item("name"))

    for i in properties.values():
        i.parent = None
        i.post_traverse(callbacks)


def build_resource_config(api_info, properties, resource_name,
                          resource_desc, version, **kwargs):

    _set_attributes(api_info, properties)

    _set_output(properties)

    resource = _Resource(resource_name, resource_desc, properties)

    resource.version = version

    return resource.render()

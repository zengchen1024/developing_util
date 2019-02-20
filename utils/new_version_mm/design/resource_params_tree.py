import re

from adjust import adjust
from common.api import build_resource_api_info
from common.parameter import build_resource_params


def generate_resource_properties(api_yaml, all_models, tag, custom_configs):

    api_info = build_resource_api_info(api_yaml, all_models,
                                       custom_configs.get("apis", {}))

    path_params = _get_all_path_params(api_info)
    _check_path_params(path_params, api_info)

    properties = build_resource_params(api_info, all_models)

    adjust(custom_configs.get("adjust", []), properties)

    _set_property(api_info, properties)
    _set_output(properties)

    _rename_path_params(api_info, path_params, properties)

    return api_info, properties


def _get_all_path_params(api_info):
    r = {}
    for k, v in api_info.items():
        for p in re.findall(r"{[^/]*}", v["api"]["path"]):
            n = p[1:][:-1]
            # path_parameter is set in the custom config file for each api
            # especially for action api
            if n not in v.get("path_parameter", []):
                r.setdefault(n, []).append(k)

    r.pop("id", None)
    return r


def _check_path_params(params, api_info):
    create_params = [i["name"] for i in api_info["create"]["body"]]

    for n, k in params.items():
        if n not in create_params:
            raise Exception("The path parameters(%s) of api(%s) doesn't exist "
                            "in the create parameters" % (n, ", ".join(k)))


def _rename_path_params(api_info, params, properties):
    create_op_id = api_info["create"]["op_id"]

    for n, ks in params.items():
        for item in properties.values():
            path = item.path.get(create_op_id)
            if path is None:
                continue

            if n == path.split(".")[-1]:
                if n != item.get_item("name"):
                    for k in ks:
                        api_info[k]["api"]["path"] = re.sub(
                            r"{%s}" % n, "{%s}" % item.get_item("name"),
                            api_info[k]["api"]["path"]
                        )
                break

        else:
            raise Exception("Can't find the path paarameter(%s) of"
                            " api(%s)" % (n, ", ".join(k)))


def _set_output(properties):
    def _output(n):
        p = n.parent
        if n.get_item("crud") == 'r' and (
                p is None or p.get_item("crud") != 'r'):
            n.set_item("output", True)

    for v in properties.values():
        v.parent = None
        v.traverse(_output)


def _set_property(api_info, properties):
    info = {v["op_id"]: v["crud"] for v in api_info.values()}

    def _set_crud(n, leaf):
        m = {"c": 0, "r": 0, "u": 0, "d": 0}

        if leaf:
            for v in n.path:
                m[info[v]] = 1

        else:
            for i in n.childs():
                for j in i.get_item("crud"):
                    m[j] = 1

        n.set_item("crud", "".join([i for i in "cru" if m[i]]))

    def _set_field(n):
        if n.get_item("crud").find("r") != -1:
            for k, v in n.path.items():
                if info[k] == "r":
                    n.set_item("field", v)

    def callbacks(n, leaf):
        _set_crud(n, leaf)
        _set_field(n)

    for i in properties.values():
        i.parent = None
        i.post_traverse(callbacks)

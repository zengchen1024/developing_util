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

    _rename_path_params(api_info["create"]["op_id"],
                        path_params, properties)

    return api_info, properties


def _get_all_path_params(api_info):
    ignore = set(["project", "project_id", "tenant"])

    r = {}
    for k, v in api_info.items():
        api = v["api"]
        if k in ["update", "read", "delete"]:
            ignore.add(
                re.findall(r"{[A-Za-z_0-9]+}", api["path"])[-1][1:][:-1])

        p = []
        for i in api.get("path_params", []):
            if i["name"] not in ignore:
                p.append(i)
        if p:
            r[v["op_id"]] = p

    return r


def _check_path_params(params, api_info):
    create_params = [i["name"] for i in api_info["create"]["body"]]
    for k, ps in params.items():
        for v in ps:
            n = v["name"]
            if n not in create_params:
                raise Exception("The path parameters(%s) of api(%s) doesn't "
                                "exist in the create parameters" % (n, k))


def _rename_path_params(create_op_id, params, properties):
    for k, ps in params.items():
        for v in ps:
            n = v["name"]

            for item in properties.values():
                path = item.path.get(create_op_id)
                if path is None:
                    continue

                if n == path.split(".")[-1]:
                    v["name"] = item.get_item("name")
                    break

            else:
                raise Exception("Can't find the path paarameter(%s) of"
                                " api(%s)" % (n, k))


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

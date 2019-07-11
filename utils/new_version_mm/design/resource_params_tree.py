import re

from adjust import adjust
from common.api import build_resource_api_info
from common import mm_param
from common.utils import fetch_api
from parameter import build_resource_params


def generate_resource_properties(api_yaml, all_models, custom_configs):

    api_info = build_resource_api_info(api_yaml, all_models,
                                       custom_configs.get("apis", {}))

    properties = build_resource_params(api_info)

    adjust(custom_configs.get("adjust", []), properties, api_info)

    _change_path_parameter(api_info, properties)

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

    return r


def _new_name_of_path_param(api_info, params, properties):
    create_op_id = fetch_api(api_info, "create")["api_index"]
    r = {}
    for n in params:
        v = []
        for item in properties.values():
            if not isinstance(item, (mm_param.MMString, mm_param.MMBoolean,
                                     mm_param.MMInteger)):
                continue

            path = item.path.get(create_op_id)
            if path is None:
                continue

            if n == path.split(".")[-1]:
                v.append(item.get_item("name"))

        if len(v) == 0:
            raise Exception("Can't find the path parameter(%s) of api(%s), "
                            "maybe you need add it manually with command of "
                            "'add_path_param'" % (n, ", ".join(params[n])))
        elif len(v) != 1:
            raise Exception("find more than one properties(%s) which are "
                            "corresponding to path parameter(%s) of api(%s)"
                            "" % (", ".join(v), n, ", ".join(params[n])))
        r[n] = v[0]

    return r


def _path_parameter_resource_id(apis):
    val = [
        fetch_api(apis, "read"),
        fetch_api(apis, "delete"),
        fetch_api(apis, "update"),
    ]
    rid = []
    for v in val:
        if not v:
            continue

        path = v["api"]["path"]
        s = re.search(r"{[A-Za-z0-9_]+}$", path)
        if s:
            rid.append(path[s.start() + 1: s.end() - 1])

    if len(set(rid)) == 1:
        return rid.pop()

    raise Exception("can't verify the path parameter of resource id")


def _change_path_parameter(api_info, properties):
    old_params = _get_all_path_params(api_info)

    p = _path_parameter_resource_id(api_info)

    # if p exists, and not remove it, then it will except in
    # _new_name_of_path_param
    v = old_params.pop(p, None)

    new_params = _new_name_of_path_param(api_info, old_params, properties)

    if p:
        old_params[p] = v
        new_params[p] = "id"

    for o, n in new_params.items():
        if o != n:
            for i in old_params[o]:
                api_info[i]["api"]["path"] = re.sub(
                    r"{%s}" % o, "{%s}" % n, api_info[i]["api"]["path"])

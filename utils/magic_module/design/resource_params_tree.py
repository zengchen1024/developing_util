import re

from adjust import adjust
from common.resource_api import build_resource_api_info
from common.resource_parameters import build_resource_params


def generate_resource_properties(api_yaml, all_models, tag, custom_configs):

    api_info = build_resource_api_info(api_yaml, all_models, tag,
                                       custom_configs.get("preprocess", {}))

    path_params = _get_all_path_params(api_info)
    _check_path_params(path_params, api_info)

    properties = build_resource_params(api_info, all_models)

    adjust(custom_configs.get("adjust", []), properties)

    _rename_path_params(path_params, properties)

    return api_info, properties


def _get_all_path_params(api_info):
    ignore = set(["project", "project_id", "tenant"])

    r = {}
    for k, v in api_info.items():
        api = v["api"]
        if k in ["update", "get", "delete"]:
            ignore.add(
                re.findall(r"{[A-Za-z_0-9]+}", api["path"])[-1][1:][:-1])

        p = []
        for i in api.get("path_params", []):
            if i["name"] not in ignore:
                p.append(i)
        if p:
            r[api["op_id"]] = p

    return r


def _check_path_params(params, api_info):
    create_params = [i["name"] for i in api_info["create"]["body"]]
    for k, v in params.items():
        n = v["name"]
        if n not in create_params:
            raise Exception("The path parameters(%s) of api(%s) doesn't exist "
                            "in the create parameters" % (n, k))


def _rename_path_params(params, properties):
    for k, v in params.items():
        n = v["name"]

        for item in properties.values():
            if n == item.get_item("field")["create"]:
                v["name"] = item.get_item("name")
                break

        else:
            raise Exception("Can't find the path paarameter(%s) of"
                            " api(%s)" % (n, k))

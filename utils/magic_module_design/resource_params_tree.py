import pystache
import re

from custom_config import custom_config
from resource_api import build_resource_api_info
from resource_parameters import build_resource_params
from utils import build_path


def generate_resource_parameter_tree(api_yaml, all_models, tag_info,
                                     custom_configs):
    api_info = build_resource_api_info(
        api_yaml, all_models, tag_info["name"],
        custom_configs.get("preprocess", {}))

    properties, parameters = build_resource_params(
        api_info, all_models, {})

    ignore = set(["project", "project_id"])
    for k, v in api_info.items():
        if k in ["update", "get", "delete"]:
            ignore.add(
                re.findall(r"{[A-Za-z_0-9]+}", v["api"]["path"])[-1][1:][:-1])

        for i in v["api"].get("path_params", []):
            n = i["name"]
            if n in ignore:
                continue

            if n not in properties and (not parameters or n not in parameters):
                raise Exception("The path parameters(%s) of api(%s) "
                                "doesn't belong to the parameter set of "
                                "CRUD api" % (n, v["api"]["op_id"]))

    if parameters:
        properties.update(parameters)

    custom_config(custom_configs, properties, {}, None)

    return _generate_yaml(properties)


def _generate_yaml(params, n=0):
    r = []
    keys = sorted(params.keys())
    for k in keys:
        v = params[k]
        s = v.to_param_yaml(n)
        if s:
            r.extend(s)
    return r

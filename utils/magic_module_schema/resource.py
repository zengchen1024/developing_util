import pystache
import re

from custom_config import custom_config
from resource_api import build_resource_api_info
from resource_parameters import build_resource_params
from utils import build_path


def build_resource_config(api_yaml, all_models, tag_info, custom_configs):
    api_info = build_resource_api_info(
        api_yaml, all_models, tag_info["name"], custom_configs)

    properties, parameters = build_resource_params(api_info, all_models)

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

    if custom_configs:
        custom_config(custom_configs, parameters, properties, api_info)

    r = [_generate_resource_config(api_info, tag_info, custom_configs)]
    r.extend(_generate_parameter_config(properties, parameters))
    return r


def _generate_resource_config(api_info, tag_info, custom_configs):
    msg_prefix = {}
    for i in ["create", "update", "get"]:
        s = api_info.get(i, {}).get("msg_prefix", None)
        if s:
            msg_prefix[i] = s

    create_api = api_info["create"]["api"]
    rn = tag_info["name"]
    if custom_configs:
        rn = custom_configs.get("resource_name", rn)
    if isinstance(rn, unicode):
        raise Exception("Must config resouce_name in English, "
                        "because the tag is Chinese")

    data = {
        "name": rn[0].upper() + rn[1:].lower(),
        "service_type": create_api["service_type"],
        "base_url": build_path(create_api["path"]),
        "msg_prefix": msg_prefix,
        "description": tag_info.get("description", ""),
        "create_verb": api_info["create"]["create_verb"],
    }

    if "update" in api_info:
        data["update_verb"] = build_path(
            api_info["update"]["update_verb"])

    if "list" in api_info:
        info = api_info["list"]
        if "identity" not in info:
            raise Exception("Must config identity for list operation")

        api = info["api"]
        v = {
            "path" : build_path(api["path"]),
            "identity": [{"name": i} for i in info["identity"]]
        }
        v["query_params"] = [{"name": i["name"]} for i in api["query_params"]]
        if "msg_prefix" in info:
            v["msg_prefix"] = info["msg_prefix"]
        data["list_info"] = v

    return pystache.Renderer().render_path("template/resource.mustache", data)


def _generate_parameter_config(properties, parameters):

    def _generate_yaml(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            s = v.to_yaml(n)
            if s:
                r.extend(s)
        return r

    result = []
    indent = 4
    if parameters:
        result.append("%sparameters:\n" % (' ' * indent))
        result.extend(_generate_yaml(parameters, indent + 2))

    result.append("%sproperties:\n" % (' ' * indent))
    result.extend(_generate_yaml(properties, indent + 2))
    return result

import pystache

from custom_config import custom_config
from resource_api import build_resource_api_info
from resource_parameters import build_resource_params
import utils


def build_resource_config(api_yaml, all_models, tag_info, custom_configs):
    api_info = build_resource_api_info(api_yaml, all_models, tag_info["name"])

    properties, parameters = build_resource_params(api_info, all_models)

    if custom_configs:
        custom_config(custom_configs, parameters, properties)

    r = [_generate_resource_config(api_info, tag_info)]
    r.extend(_generate_parameter_config(properties, parameters))
    return r


def _generate_resource_config(api_info, tag_info):
    msg_prefix = {}
    for i in ["create", "update", "get", "list"]:
        s = api_info.get(i, {}).get("msg_prefix", None)
        if s:
            msg_prefix[i] = s

    create_api = api_info["create"]["api"]
    service_type = create_api["service_type"]
    tag = tag_info["name"]
    data = {
        "name": service_type.upper() + tag[0].upper() + tag[1:].lower(),
        "service_type": service_type,
        "base_url": utils.build_path(create_api["path"]),
        "msg_prefix": msg_prefix,
        "description": tag_info.get("description", ""),
        "create_verb": api_info["create"]["create_verb"],
    }

    if "list" in api_info:
        data["list_url"] = utils.build_path(
            api_info["list"]["api"]["path"])

    if "update" in api_info:
        data["update_verb"] = utils.build_path(
            api_info["update"]["update_verb"])

    return pystache.Renderer().render_path("template/resource.mustache", data)


def _generate_parameter_config(properties, parameters):

    def _generate_yaml(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            r.extend(v.to_yaml(n))
        return r

    result = []
    indent = 4
    if parameters:
        result.append("%sparameters:\n" % (' ' * indent))
        result.extend(_generate_yaml(parameters, indent + 2))

    result.append("%sproperties:\n" % (' ' * indent))
    result.extend(_generate_yaml(properties, indent + 2))
    return result

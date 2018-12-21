import re

from adjust import adjust
from resource_api import build_resource_api_info
from resource_parameters import build_resource_params


def generate_resource_parameter_tree(api_yaml, all_models, tag_info,
                                     custom_configs):

    api_info = build_resource_api_info(api_yaml, all_models, tag_info["name"],
                                       custom_configs.get("preprocess", {}))

    _check_path_parameter(api_info)

    properties, parameters = build_resource_params(api_info, all_models)

    adjust(custom_configs.get("adjust", []), properties, parameters, None)


def _check_path_parameter(api_info):
    ignore = set(["project", "project_id", "tenant"])
    create_params = [i["name"] for i in api_info["create"]["body"]]

    for k, v in api_info.items():
        if k in ["update", "get", "delete"]:
            ignore.add(
                re.findall(r"{[A-Za-z_0-9]+}", v["api"]["path"])[-1][1:][:-1])

        for i in v["api"].get("path_params", []):
            n = i["name"]
            if n in ignore:
                continue

            if n not in create_params:
                raise Exception("The path parameters(%s) of api(%s) "
                                "doesn't exist in the create parameters" % (
                                    n, v["api"]["op_id"]))

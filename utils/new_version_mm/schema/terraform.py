import os
import pystache
import re

from common.utils import write_file, find_property
from common.preprocess import find_parameter


def build_terraform_yaml(info, all_models, output):
    data = []
    for v in info:
        config = v.get("custom_configs").get("terraform")
        if not config:
            continue

        r = {}
        examples = config.get("examples")
        if examples:
            r.update(_generate_example_config(examples, v))

        c = config.get("overrides")
        if c:
            _generate_override(
                c, v["api_info"], v["properties"], all_models,
                v["resource_name"], r)

        if r:
            r["name"] = v["resource_name"]
            data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])


def _generate_override(overrides, api_info, properties, all_models,
                       resource_name, result):

    property_overrides = {}
    api_parameter_overrides = {}
    api_async_overrides = {}

    for path, v in overrides.items():
        if "to_request" in v or "to_request_method" in v:
            api_parameter_overrides[path] = v

        elif "from_response" in v or "from_response_method" in v:
            property_overrides[path] = v

        elif "async_status_check_func" in v:
            api_async_overrides[path] = v

        else:
            raise Exception("find unspported override item(%s) for "
                            "resource(%s)" % (
                                " ".join(v.keys()), resource_name))

    if property_overrides:
        result.update(
            _generate_property_override(property_overrides, properties))

    if api_parameter_overrides:
        result.update(
            _generate_api_parameter_override(
                api_parameter_overrides, api_info, all_models))

    if api_async_overrides:
        result.update(
            _generate_api_async_override(api_async_overrides, api_info))


def _generate_property_override(overrides, properties):
    pros = []
    for path, v in overrides.items():

        find_property(properties, path)

        m = {"prop_path": path}

        if "from_response" in v:
            m["from_response"] = _process_lines(v.get("from_response"), 10)

        elif "from_response_method" in v:
            m["from_response_method"] = v.get("from_response_method")

        pros.append(m)

    return {
        "properties": pros,
        "has_property_override": True
    }


def _generate_api_parameter_override(overrides, api_info, all_models):
    req_apis = {
        v["op_id"]: v
        for v in api_info.values()
        if v["crud"].find("r") == -1
    }

    params = []
    for path, v in overrides.items():
        pv = path.split(".")

        api = req_apis.get(pv[0])
        if not api:
            raise Exception("the index(%s) is invalid, "
                            "unknown operation id" % path)

        path = ".".join(pv[1:])
        if api.get("msg_prefix"):
            path = path.replace(api.get("msg_prefix") + ".", "", 1)

        find_parameter(path, api["body"], all_models)

        m = {"prop_path": "%s.%s" % (api.get("type", api["op_id"]), path)}

        if "to_request" in v:
            m["to_request"] = _process_lines(v.get("to_request"), 10)

        elif "to_request_method" in v:
            m["to_request_method"] = v.get("to_request_method")

        params.append(m)

    return {
        "parameters": params,
        "has_parameter_override": True
    }


def _generate_api_async_override(overrides, api_info):
    req_apis = {
        v["op_id"]: v
        for v in api_info.values()
        if v["crud"].find("r") == -1
    }

    pros = []
    for path, v in overrides.items():
        if path not in req_apis:
            raise Exception("the index(%s) is invalid, "
                            "unknown operation id" % path)
        api = req_apis[path]
        pros.append({
            "api": api.get("type", api["op_id"]),
            "custom_status_check_func": v.get("async_status_check_func")
        })

    return {
        "api_asyncs": pros,
        "has_async_override": True
    }


def _process_lines(v, indent):
    return "\n".join([
        "%s%s" % (' ' * indent, row.strip("\t"))
        for row in v.split("\n")
    ])


def _generate_example_config(examples, info):
    trn = ("%s_%s_%s_%s" % (
        info["cloud_full_name"], info["service_type"],
        info["resource_name"], info["version"])).lower()

    m = re.compile(r"resource \"%s\" \"(.*)\" {" % trn)

    def _find_id(f):
        tf = None
        with open(f, "r") as o:
            tf = o.readlines()

        r = []
        for i in tf:
            v = m.match(i)
            if v:
                r.append(v)

        if len(r) != 1:
            raise Exception("Find zero or one more terraform resource(%s) "
                            "in tf file(%s)" % (trn, f))

        return r[0].group(1)

    result = [
        {
            "name": os.path.basename(f["path"]).split(".")[0],
            "resource_id": _find_id(info["config_dir"] + f["path"]),
            "description": f["description"]
        }
        for f in examples
    ]
    if result:
        result[0]["is_basic"] = True

    return {"examples": result, "has_example": len(result) > 0}

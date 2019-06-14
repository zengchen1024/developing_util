import os
import pystache

from common.utils import (find_property, process_override_codes,
                          read_yaml, underscore, write_file)
from common.preprocess import find_parameter


def build_ansible_yaml(info, all_models, output):
    data = []
    for v in info:
        config = v.get("custom_configs").get("ansible")
        if not config:
            continue

        r = {}
        examples = config.get("examples")
        if examples:
            _generate_example_config(examples, v, output)

        c = config.get("overrides")
        if c:
            _generate_override(
                c, v["api_info"], v["properties"], all_models,
                v["resource_name"], r)

        if r:
            r["name"] = v["resource_name"]
            data.append(r)

    s = pystache.Renderer().render_path("template/ansible.mustache",
                                        {"resources": data})

    write_file(output + "ansible.yaml", [s])


def _generate_override(overrides, api_info, properties, all_models,
                       resource_name, result):

    property_overrides = {}
    api_parameter_overrides = {}
    api_async_overrides = {}
    api_multi_invoke_overrides = {}

    for path, v in overrides.items():
        if not isinstance(v, dict):
            raise Exception("the override(%s) is not in correct format" % path)

        if "to_request" in v or "to_request_method" in v:
            api_parameter_overrides[path] = v

        elif "from_response" in v:
            property_overrides[path] = v

        elif "async_status_check_func" in v:
            api_async_overrides[path] = v

        elif "parameter_pre_process" in v:
            api_multi_invoke_overrides[path] = v

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

    if api_multi_invoke_overrides:
        result.update(
            _generate_api_multi_invoke_override(
                api_multi_invoke_overrides, api_info))


def _generate_property_override(overrides, properties):
    k = "from_response"
    pros = []
    for path, v in overrides.items():

        find_property(properties, path)

        pros.append({
            "prop_path": path,
            k: process_override_codes(v.get(k), 10)
        })

    return {
        "properties": pros,
        "has_property_override": True
    }


def _generate_api_parameter_override(overrides, api_info, all_models):
    req_apis = {
        v["op_id"]: v
        for v in api_info.values()
        if v["crud"].find("r") == -1 or v.get("type", "") == "list"
    }

    params = []
    for path, v in overrides.items():
        pv = path.split(".")

        api = req_apis.get(underscore(pv[0]))
        if not api:
            raise Exception("the index(%s) is invalid, "
                            "unknown operation id" % path)

        path = ".".join(pv[1:])
        if api.get("msg_prefix"):
            path = path.replace(api.get("msg_prefix") + ".", "", 1)

        find_parameter(path, api["body"], all_models)

        m = {"prop_path": "%s.%s" % (api.get("type", api["op_id"]), path)}

        if "to_request" in v:
            m["to_request"] = process_override_codes(v.get("to_request"), 10)

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
        path1 = underscore(path)
        if path1 not in req_apis:
            raise Exception("the index(%s) is invalid, "
                            "unknown operation id" % path)
        api = req_apis[path1]
        pros.append({
            "api": api.get("type", api["op_id"]),
            "custom_status_check_func": v.get("async_status_check_func")
        })

    return {
        "api_asyncs": pros,
        "has_async_override": True
    }


def _generate_api_multi_invoke_override(overrides, api_info):
    req_apis = {
        v["op_id"]: v
        for v in api_info.values()
        if v["crud"].find("r") == -1
    }

    pros = []
    for path, v in overrides.items():
        path1 = underscore(path)
        if path1 not in req_apis:
            raise Exception("the index(%s) is invalid, "
                            "unknown operation id" % path)
        api = req_apis[path1]
        pros.append({
            "api": api.get("type", api["op_id"]),
            "parameter_pre_process": process_override_codes(
                v.get("parameter_pre_process"), 10)
        })

    return {
        "api_multi_invokes": pros,
        "has_multi_invoke_override": True
    }


def _generate_example_config(examples, info, output):
    module_name = underscore("%s_%s_%s" % (
        info["cloud_short_name"], info["service_type"],
        info["resource_name"]))

    output += "examples/ansible/"
    if not os.path.isdir(output):
        os.makedirs(output)

    for f in examples:
        data = _build_example_render_info(
            info["config_dir"] + f, module_name, info["cloud_short_name"])

        s = pystache.Renderer().render_path(
            "template/ansible_example.mustache", data)

        write_file(output + os.path.basename(f), [s])


def _build_example_render_info(f, module_name, cloud_short_name):
    tasks = None
    r = read_yaml(f)
    if len(r) == 1 and isinstance(r[0], dict) and "tasks" in r[0]:
        tasks = r[0].get("tasks")
    else:
        raise Exception("the format of example is not correct")

    if not tasks:
        raise Exception("no tasks in the example file")

    task = None
    for i in tasks:
        if module_name in i:
            task = i
            tasks.remove(i)
            break
    else:
        raise Exception("can't find the task(%s)" % module_name)

    v = {
        "example_description": r[0].get("name"),
        "task_name": module_name,
        "task_code": _build_module_params(task[module_name], 4),
        "task_description": task.get("name")
    }

    if tasks:
        d = []
        for t in tasks:
            module = ""
            for k in t:
                if k.startswith(cloud_short_name):
                    module = k
                    break
            else:
                continue

            d.append({
                "name": module,
                "register": t.get("register"),
                "description": t.get("name"),
                "code": _build_module_params(t[module], 6),
            })

        if d:
            v["depends"] = d
            v["has_depends"] = True

    return v


def _build_module_params(params, spaces, array_item=False):
    v = ["identity_endpoint", "user", "password",
         "domain", "project", "log_file"]
    for i in v:
        params.pop(i, None)

    return _gen_module_params(params, spaces, array_item)


def _gen_module_params(params, spaces, array_item=False):
    r = []
    for k, v in params.items():

        if isinstance(v, dict):
            r.append("%s%s:" % (' ' * spaces, k))
            r.append(_gen_module_params(v, spaces + 2))

        elif isinstance(v, list):
            r.append("%s%s:" % (' ' * spaces, k))

            if isinstance(v[0], dict):
                r.append(_gen_module_params(v, spaces + 4), True)
            else:
                if isinstance(v[0], str):
                    for i in v:
                        r.append("%s- \"%s\"" % (' ' * (spaces + 2), str(i)))
                else:
                    for i in v:
                        r.append("%s- %s" % (' ' * (spaces + 2), str(i)))

        else:
            if isinstance(v, str):
                r.append("%s%s: \"%s\"" % (' ' * spaces, k, str(v)))
            else:
                r.append("%s%s: %s" % (' ' * spaces, k, str(v)))

    if array_item:
        r[0] = "%s- %s" % (' ' * (spaces - 2), r[0].strip())

    return "\n".join(r)

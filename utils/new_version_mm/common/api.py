import re

from preprocess import find_parameter
from preprocess import find_struct
from preprocess import preprocess
from utils import underscore


def _get_array_path(index, body, all_models):
    if not index:
        return []

    r = []
    items = index.split(".")
    for i in range(len(items)):
        s = ".".join(items[:(i + 1)])
        j, parent = find_parameter(s, body, all_models)
        item = parent[j]
        if item.get("is_array"):
            r.append(s)

    return r


def _build_parameter(body, all_models, custom_config):
    if len(body) == 0:
        raise Exception("Can't parse message prefix, the struct is empty")

    special_cmds = {
        "set_value": {},
        "depends_on": {},
        "allow_empty": {},
        "set_array_num": {}
    }
    cmds = custom_config.get("parameter_preprocess", [])
    if cmds and isinstance(cmds, list):
        preprocess(body, all_models, cmds)

        for i in cmds:
            for j in special_cmds:
                if i.find(j) != -1:
                    v = re.sub(r" +", " ", i).split(" ")
                    special_cmds[j][v[1]] = v[2] if len(v) > 2 else None

    array_path = []
    path = custom_config.get("path_to_body")
    if path:
        array_path = _get_array_path(path, body, all_models)

        i, parent = find_parameter(path, body, all_models)
        body = find_struct(parent[i]["datatype"], all_models)

        for k, v in special_cmds.items():
            if v:
                special_cmds[k] = {
                    k1.replace(path + ".", "", 1): v1 for k1, v1 in v.items()}

    return {
        "msg_prefix": path,
        "body": body,
        "special_cmds": special_cmds,
        "msg_prefix_array_items": array_path,
    }


def _create_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build create parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(all_models.get(p), all_models, custom_config)

    r["crud"] = "c"

    if "async" not in custom_config:
        p = custom_config.get("resource_id_path")
        if not p:
            raise Exception("Must set resource id path for create api")

        r["resource_id_path"] = p

    return r


def _delete_api_info(api, all_models, custom_config):
    r = {"crud": "d"}

    p = api.get("request_body", {}).get("datatype", "")
    if p in all_models:
        v = _build_parameter(all_models.get(p), all_models, custom_config)

        r.update(v)

    return r


def _update_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build update parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(all_models.get(p), all_models, custom_config)

    r["crud"] = "u"
    return r


def _read_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build get parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(all_models.get(p), all_models, custom_config)
    r["crud"] = "r"

    return r


def _list_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build list response body parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(all_models.get(p), all_models, custom_config)

    # body of list must be array, don't parse it as a map
    if r["msg_prefix"] in r["msg_prefix_array_items"]:
        r["msg_prefix_array_items"].remove(r["msg_prefix"])

    # identity is only needed by Terraform
    identity = custom_config.get("identity")
    if identity:
        m = [i["name"] for i in r["body"]]
        for i in identity:
            if i not in m:
                raise Exception(
                    "Unknown identity parameter(%s) for list api" % i)

    p = custom_config.get("resource_id_path")
    if not p:
        raise Exception("Must set resource id path for list api")

    m = custom_config.get("query_param_map")
    if m:
        qp = [i["name"] for i in api.get("query_params", [])]
        for k, v in m.items():
            if k not in qp:
                raise Exception("the parameter(%s) in query_param_map is not"
                                "a valid query parameter" % k)

            find_parameter(v, r["body"], all_models)

            array_path = _get_array_path(v, r["body"], all_models)
            if array_path:
                raise Exception(
                    "can not specify the property(%s) belonging "
                    "to an array for the query parameter(%s)" % (v, k))

    r.update({
        "resource_id_path": p,
        "identity": identity,
        "crud": 'r',
        "query_param_map": m
    })
    return r


def _other_api_info(api, all_models, custom_config):
    r = {}
    crud = ""
    if "when" in custom_config:
        r["when"] = custom_config["when"]

        crud = {
            "after_send_create_request": "c"
        }[r["when"]]
    else:
        crud = custom_config.get("crud")

    if not crud:
        raise Exception("Must set crud for none standard "
                        "create/read/update/delete/list api")
    r["crud"] = crud

    p = ""
    if crud.find("r") != -1:
        p = api.get("response", {}).get("datatype", "")
    else:
        p = api.get("request_body", {}).get("datatype", "")

    if p in all_models:
        v = _build_parameter(all_models.get(p), all_models, custom_config)
        r.update(v)

    return r


def _remove_project(api_info):
    def _f(path):
        s = re.search(
            r"{project_id}/|{project}/|{tenant}/|{tenant_id}/|{projectId}",
            path)
        if s:
            return path[s.end():]

        return path

    api_info["api"]["path"] = _f(api_info["api"]["path"]).lstrip("/")

    v = api_info["async"]
    if v:
        q = v.get("query_status")
        if q:
            q["path"] = _f(q["path"]).lstrip("/")


def build_resource_api_info(api_yaml, all_models, custom_configs):
    m = {
        "create": _create_api_info,
        "read": _read_api_info,
        "delete": _delete_api_info,
        "update": _update_api_info,
        "list": _list_api_info,
    }
    result = {}
    for k, v in custom_configs.items():
        op_id = underscore(k)
        api = api_yaml.get(op_id)
        if not api:
            raise Exception("Unknown opertion id:%s" % k)

        t = v.get("type")
        if t:
            if t not in m:
                raise Exception("Unknown api type(%s)" % t)

            r = m[t](api, all_models, v)
            r["type"] = t
        else:
            r = _other_api_info(api, all_models, v)

        r["op_id"] = op_id
        r["api"] = api
        r["verb"] = api["method"].upper()
        r["async"] = v.get("async")

        if v.get("exclude_for_schema"):
            r["exclude_for_schema"] = True

        for k in ["path_parameter", "header_params", "service_type"]:
            v1 = v.get(k)
            if v1:
                r[k] = v1

        _remove_project(r)

        k1 = t
        if not k1:
            k1 = op_id
        result[k1] = r

    # avoid generating properties of both read and list
    if "read" in result and "list" in result:
        result["list"]["exclude_for_schema"] = True

    return result

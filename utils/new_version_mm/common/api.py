import copy
import re

from preprocess import find_parameter
from preprocess import find_struct
from preprocess import preprocess
from utils import (fetch_api, underscore)


def _retrive_structs(key, all_models):
    s = all_models[key]
    r = {key: s}

    for p in s:
        dt = p["datatype"]

        if dt in all_models:
            r.update(_retrive_structs(dt, all_models))

        elif dt.find("list") == 0:
            sub_dt = re.match(r"list\[(.*)\]", dt).group(1)
            if sub_dt in all_models:
                r.update(_retrive_structs(sub_dt, all_models))
    return r


def _copy_structs(key, all_models):
    return copy.deepcopy(_retrive_structs(key, all_models))


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


def _build_parameter(key, all_models, custom_config):
    structs = _copy_structs(key, all_models)
    body = structs[key]
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
        preprocess(body, structs, cmds)

        for i in cmds:
            for j in special_cmds:
                if i.find(j) != -1:
                    v = re.sub(r" +", " ", i).split(" ")
                    special_cmds[j][v[1]] = v[2] if len(v) > 2 else None

    array_path = []
    path = custom_config.get("path_to_body")
    if path:
        array_path = _get_array_path(path, body, structs)

        i, parent = find_parameter(path, body, structs)
        body = find_struct(parent[i]["datatype"], structs)

        for k, v in special_cmds.items():
            if v:
                special_cmds[k] = {
                    k1.replace(path + ".", "", 1): v1 for k1, v1 in v.items()}

    return {
        "msg_prefix": path,
        "body": body,
        "all_models": structs,
        "special_cmds": special_cmds,
        "msg_prefix_array_items": array_path,
    }


def _create_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build create parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(p, all_models, custom_config)

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
        v = _build_parameter(p, all_models, custom_config)

        r.update(v)

    return r


def _update_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build update parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(p, all_models, custom_config)

    r["crud"] = "u"
    return r


def _read_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build get parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(p, all_models, custom_config)
    r["crud"] = "r"

    return r


def _list_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build list response body parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(p, all_models, custom_config)

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

            find_parameter(v, r["body"], r["all_models"])

            array_path = _get_array_path(v, r["body"], r["all_models"])
            if array_path:
                raise Exception(
                    "can not specify the property(%s) belonging "
                    "to an array for the query parameter(%s)" % (v, k))

    r.update({
        "resource_id_path": p,
        "identity": identity,
        "crud": 'r',
        "query_param_map": m,
        "pagination_offset": custom_config.get("pagination_offset"),
        "pagination_start": custom_config.get("pagination_start"),
        "pagination_marker": custom_config.get("pagination_marker"),
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

    elif "multi_invoke" in custom_config:
        r["multi_invoke"] = custom_config.get("multi_invoke")
        crud = custom_config.get("crud")

        v = custom_config.get("depends_on")
        if not v:
            raise Exception("Must set depends_on for multiple invoke api")
        r["depends_on"] = v

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
        v = _build_parameter(p, all_models, custom_config)
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


def _build_api_info(api_type, api, all_models, custom_config):
    m = {
        "create": _create_api_info,
        "read": _read_api_info,
        "delete": _delete_api_info,
        "update": _update_api_info,
        "list": _list_api_info,
    }

    return m.get(api_type, _other_api_info)(api, all_models, custom_config)


def build_resource_api_info(api_yaml, all_models, custom_configs):
    apis = {underscore(k): k for k in custom_configs}
    if len(apis) != len(custom_configs):
        raise Exception("There are same indexes for apis. Note: the api "
                        "index is case insensitive")

    result = {}
    for k, k1 in apis.items():
        cc = custom_configs[k1]

        op_id = str(cc.get("operation_id", ""))
        if not op_id:
            raise Exception("Must set operation_id for api(%s)" % k1)

        api = api_yaml.get(underscore(op_id))
        if not api:
            raise Exception("Unknown opertion id:%s" % op_id)

        r = _build_api_info(k, api, all_models, cc)

        if len(r["crud"]) != 1:
            raise Exception(
                "The crud of api(%s) must be one of c, r, u, d" % k)

        r["name"] = k
        r["api_index"] = k
        r["op_id"] = op_id
        r["api"] = api
        r["has_response_body"] = (
            api.get("response", {}).get("datatype") in all_models)
        r["verb"] = api["method"].upper()
        r["async"] = cc.get("async")

        if cc.get("exclude_for_schema"):
            r["exclude_for_schema"] = True

        for i in ["path_parameter", "header_params",
                  "service_type", "success_codes"]:
            if i in cc:
                r[i] = cc[i]

        _remove_project(r)

        result[k] = r

    # avoid generating properties of both read and list
    read_api = fetch_api(result, "read")
    list_api = fetch_api(result, "list")
    if read_api and list_api:
        list_api["exclude_for_schema"] = True

    for i in ["create", "delete"]:
        if fetch_api(result, i) is None:
            raise Exception("Must configue %s api" % i)

    return result

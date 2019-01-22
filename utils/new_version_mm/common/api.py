import re

from preprocess import preprocess


def _build_parameter(body, all_models, custom_config):
    cmds = custom_config.get("parameter_preprocess")
    if cmds:
        preprocess(body, all_models, cmds)

    msg_prefix = None
    if len(body) == 1:
        p = body[0]
        if p and p["datatype"] in all_models:
            msg_prefix = p["name"]
            body = all_models[p["datatype"]]

    return msg_prefix, body


def _create_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build create parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix, body = _build_parameter(
        all_models.get(p), all_models, custom_config)

    p = custom_config.get("resource_id_path")
    if not p:
        raise Exception("Must set resource id path for create api")

    return {
        "msg_prefix": msg_prefix,
        "body": body,
        "crud": "c",
        "resource_id_path": p
    }


def _read_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build get parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix, body = _build_parameter(
        all_models.get(p), all_models, custom_config)

    return {
        "msg_prefix": msg_prefix,
        "body": body,
        "crud": "r"
    }


def _delete_api_info(api, all_models, custom_config):
    return {
        "crud": "d"
    }


def _update_api_info(api, all_models, custom_config):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build update parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix, body = _build_parameter(
        all_models.get(p), all_models, custom_config)

    return {
        "msg_prefix": msg_prefix,
        "body": body,
        "crud": "u"
    }


def _list_api_info(api, all_models, custom_config):
    i = custom_config.get("identity")
    if not i:
        raise Exception("Must set identity for list api")

    return {
        "identity": i,
        "crud": 'r'
    }


def _other_api_info(api, all_models, custom_config):
    crud = custom_config.get("crud")
    if not crud:
        raise Exception("Must set crud for none standard "
                        "create/read/update/delete/list api")

    if crud.find("r") != -1:
        p = api.get("response", {}).get("datatype", "")
    else:
        p = api.get("request_body", {}).get("datatype", "")

    r = {}
    if p in all_models:
        msg_prefix, body = _build_parameter(
            all_models.get(p), all_models, custom_config)

        r["msg_prefix"] = msg_prefix
        r["body"] = body

    r["crud"] = crud
    if "action" in custom_config:
        r["action"] = custom_config["action"]

    if custom_config.get("exclude_for_schema"):
        r["exclude_for_schema"] = True

    return r


def _remove_project(api):
    s = re.search(r"{project_id}/|{project}/|{tenant}/", api["path"])
    if s:
        api["path"] = api["path"][s.end():]


def _replace_resource_id(apis):
    rid = ""
    for i in ["read", "delete", "update"]:
        api = apis.get(i)
        if not api:
            continue

        path = api["api"]["path"]
        s = re.search(r"{[A-Za-z0-9_]+}$", path)
        if s:
            rid = path[s.start() + 1: s.end() - 1]
            break
    else:
        return

    for i in apis.values():
        i["api"]["path"] = re.sub(r"{%s}" % rid, "{id}", i["api"]["path"])


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
        api = api_yaml.get(k)
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

        r["op_id"] = k
        r["api"] = api
        r["verb"] = api["method"].upper()

        _remove_project(api)

        k1 = t
        if not k1:
            k1 = k
        result[k1] = r

    _replace_resource_id(result)
    return result

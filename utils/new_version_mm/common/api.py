import re

from preprocess import preprocess


def _build_parameter(body, all_models, custom_config):
    cmds = custom_config.get("parameter_preprocess")
    if cmds:
        preprocess(body, all_models, cmds)

    original_body = body

    msg_prefix = None
    if len(body) == 1:
        p = body[0]
        # p["datatype"] in all_models means p["datatype"] is a struct
        # here, it only parses msg_prefix for struct like {msg_prefix: {}}
        if p and p["datatype"] in all_models:
            msg_prefix = p["name"]
            body = all_models[p["datatype"]]

    return {
        "msg_prefix": msg_prefix,
        "body": body,
        "original_body": original_body
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


def _read_api_info(api, all_models, custom_config):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build get parameter, "
                        "the datatype(%s) is not a struct" % p)

    r = _build_parameter(all_models.get(p), all_models, custom_config)

    r["crud"] = "r"

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


def _list_api_info(api, all_models, custom_config):
    i = custom_config.get("identity")
    if not i:
        raise Exception("Must set identity for list api")

    return {
        "identity": i,
        "crud": 'r'
    }


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
        s = re.search(r"{project_id}/|{project}/|{tenant}/|{tenant_id}/", path)
        if s:
            return path[s.end():]

        return path

    api_info["api"]["path"] = _f(api_info["api"]["path"])

    v = api_info["async"]
    if v:
        q = v.get("query_status")
        if q:
            q["path"] = _f(q["path"])


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
        r["async"] = v.get("async")
        r["default_value"] = v.get("default_value")

        if v.get("exclude_for_schema"):
            r["exclude_for_schema"] = True

        p = v.get("path_parameter")
        if p:
            r["path_parameter"] = p

        _remove_project(r)

        k1 = t
        if not k1:
            k1 = k
        result[k1] = r

    return result

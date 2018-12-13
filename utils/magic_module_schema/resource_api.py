import re


class _ResourceApi(object):
    def __init__(self, api_yaml, tag):
        r = []
        for k, v in api_yaml.items():
            if tag in v.get("tag", []):
                path = v["path"]
                if path[-1] != "/":
                    path += "/"

                r.append((path, v["method"].lower(), k))

        if not r:
            raise Exception("Unknown tag(%s)" % tag)

        self._resouce_api = r

    def __call__(self):
        self._sort()
        apis = self._resouce_api

        if apis[0][1] not in ["post", "put"]:
            raise Exception("It can not find the create api")
        create_path = apis[0][0]

        r = {
            "create": apis[0][2],
            "get": self._find_rud_api(create_path, "get", ["get"]),
            "delete": self._find_rud_api(create_path, "delete", ["delete"])
        }

        try:
            v = self._find_rud_api(create_path, "update",
                                   ["post", "put", "patch"])
            r["update"] = v
        except Exception as ex:
            print(str(ex))

        for item in apis:
            if item[1] == "get" and item[0] == create_path:
                r["list"] = item[2]
                break
        else:
            print("It can not to find the (list) api")

        # other apis
        v = set([k[2] for k in apis]) - set(r.values())
        if v:
            r["others"] = v

        return r

    def _sort(self):

        def _cmp(x, y):
            if x[0] != y[0]:
                return len(x[0]) - len(y[0])

            m = {
                "post": 1,
                "put": 2,
            }
            return m.get(x[1], 3) - m.get(y[1], 3)

        self._resouce_api.sort(_cmp)

    def _find_rud_api(self, create_path, t, methods):
        s = len(create_path)
        for item in self._resouce_api:
            if item[1] not in methods:
                continue

            path = item[0]
            if len(path) > s and re.match(r"^{[A-Za-z_0-9]+}/$", path[s:]):
                return item[2]
                break
        else:
            raise Exception("It can not to find the (%s) api" % t)


def build_resource_api_info(api_yaml, all_models, tag, custom_configs):

    all_api = _ResourceApi(api_yaml, tag)()

    r = {
        "create": _create_api_info(api_yaml[all_api["create"]],
                                   all_models, custom_configs),
        "get": _get_api_info(api_yaml[all_api["get"]], all_models)
    }
    r["create"]["api"]["op_id"] = all_api["create"]
    r["get"]["api"]["op_id"] = all_api["get"]

    if "update" in all_api:
        k = all_api["update"]
        r["update"] = _update_api_info(api_yaml[k], all_models)
        r["update"]["api"]["op_id"] = k

    if "list" in all_api:
        k = all_api["list"]
        r["list"] = _list_api_info(api_yaml[k], all_models)
        r["list"]["api"]["op_id"] = k

    for i in all_api.get("others", []):
        v = api_yaml[i]
        v["op_id"] = i
        r["other_" + i] = {"api": v}

    return r


def _create_api_info(api, all_models, custom_configs):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build create parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix = None
    body = all_models.get(p)

    p = None
    if len(body) == 1:
        p = body[0]

    elif len(body) > 1:
        ps = custom_configs.get("properties", {})
        v = [i for i in body if "alone_parameter" not in ps.get(i["name"], {})]
        if len(v) == 1:
            p = v[0]

    if p and p["datatype"] in all_models:
        msg_prefix = p["name"]
        body = all_models[p["datatype"]]

    return {
        "api": api,
        "msg_prefix": msg_prefix,
        "body": body,
        "create_verb": api["method"].upper()
    }


def _get_api_info(api, all_models):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build get parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix = None
    body = all_models.get(p)
    p = body
    if len(p) == 1 and p[0]["datatype"] in all_models:
        msg_prefix = p[0]["name"]
        body = all_models[p[0]["datatype"]]

    return {
        "api": api,
        "msg_prefix": msg_prefix,
        "body": body
    }


def _update_api_info(api, all_models):
    p = api.get("request_body", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build update parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix = None
    body = all_models.get(p)
    p = body
    if len(p) == 1 and p[0]["datatype"] in all_models:
        msg_prefix = p[0]["name"]
        body = all_models[p[0]["datatype"]]

    return {
        "api": api,
        "msg_prefix": msg_prefix,
        "body": body,
        "update_verb": api["method"].upper()
    }


def _list_api_info(api, all_models):
    p = api.get("response", {}).get("datatype", "")
    if p not in all_models:
        raise Exception("It can not build list parameter, "
                        "the datatype(%s) is not a struct" % p)

    msg_prefix = None
    body = all_models.get(p)
    p = body
    if len(p) == 1 and p[0].get("is_array") and (
            p[0].get("items_datatype") in all_models):
        msg_prefix = p[0]["name"]
        body = all_models[p[0]["items_datatype"]]

    return {
        "api": api,
        "msg_prefix": msg_prefix,
        "body": body,
    }

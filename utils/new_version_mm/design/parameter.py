from common import mm_param


def build_resource_params(api_info):

    properties = None
    for i in "crud":
        for k, v in api_info.items():
            if v["crud"].find(i) != -1 and (not v.get("exclude_for_schema")):
                r = _build_params(v)
                if not r:
                    continue

                if properties:
                    _merge_params(properties, r)
                else:
                    properties = r

    return properties


def _build_params(api_info):

    def _init_node(n):
        if api_info["crud"].find("c") == -1:
            n.set_item("required", None)

        op = api_info["op_id"]

        if n.parent is None:
            n.path[op] = n.get_item("name")

        else:
            n.path[op] = "%s.%s" % (n.parent.path[op], n.get_item("name"))

    def _index_method(p):
        return p["alias"] if "alias" in p else p["name"]

    body = api_info.get("body")
    if body:
        r = mm_param.build(body, api_info["all_models"], _index_method)
        for v in r.values():
            v.traverse(_init_node)

        return r


def _merge_params(properties, news):

    def _callback(p1, p2, level):
        if p1 and p2:
            p2.path.update(p1.path)

    for k, v in news.items():
        if k in properties:
            properties[k].merge(v, _callback, None)

        else:
            properties[k] = v

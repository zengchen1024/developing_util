import mm_param


def build_resource_params(api_info, all_models):

    properties = None
    for i in "crud":
        for k, v in api_info.items():
            if v["crud"].find(i) != -1 and (not v.get("exclude_for_schema")):
                r = _build_params(v, all_models)
                if not r:
                    continue

                if properties:
                    _merge_params(properties, r)
                else:
                    properties = r

    return properties


def _build_params(api_info, all_models):

    def _init_node(n):
        if api_info["crud"].find("c") == -1:
            n.set_item("required", None)

        op = api_info["op_id"]
        msg_prefix = api_info["msg_prefix"]

        if n.parent is None:
            if msg_prefix is None:
                n.path[op] = n.get_item("name")
            else:
                n.path[op] = "%s.%s" % (msg_prefix, n.get_item("name"))

        else:
            n.path[op] = "%s.%s" % (n.parent.path[op], n.get_item("name"))

    body = api_info.get("body")
    if body:
        r = mm_param.build(body, all_models)
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

import mm_param


def build_resource_params(api_info, all_models):

    read = _build_read_params(api_info, all_models)

    create = _build_create_params(api_info, all_models)

    update = None
    if "update" in api_info:
        update = _build_update_params(api_info, all_models)

    print("------ start to merge create parameters to get ------")
    parameters = _merge_create_params(create, read)

    if update:
        print("------ start to merge update parameters to get ------")
        _merge_update_params(update, read, parameters)

    read.update(parameters)

    return read


def _set_property(p, kv={}):
    for k, v in kv.items():
        p.set_item(k, v)


def _set_path(n, op, msg_prefix=""):
    if n.parent is None:

        if msg_prefix is None:
            n.path[op] = n.get_item("name")
        else:
            n.path[op] = "%s.%s" % (msg_prefix, n.get_item("name"))

    else:
        n.path[op] = "%s.%s" % (n.parent.path[op], n.get_item("name"))


def _build_read_params(api_info, all_models):
    api = api_info["read"]

    def _init_node(n):
        _set_property(n, {"required": None})
        _set_path(n, api["api"]["op_id"], api["msg_prefix"])

    read = mm_param.build(api["body"], all_models)
    for v in read.values():
        v.traverse(_init_node)

    return read


def _build_create_params(api_info, all_models):
    api = api_info["create"]

    def _init_node(n):
        _set_path(n, api["api"]["op_id"], api["msg_prefix"])

    create = mm_param.build(api["body"], all_models)
    for v in create.values():
        v.traverse(_init_node)

    return create

def _build_update_params(api_info, all_models):
    api = api_info["update"]

    def _init_node(n):
        _set_property(n, {"required": None})
        _set_path(n, api["api"]["op_id"], api["msg_prefix"])

    update = mm_param.build(api["body"], all_models)
    for v in update.values():
        v.traverse(_init_node)

    return update


def _merge_create_params(create, read):
    parameters = {}
    for k, v in create.items():

        if k in read:
            read[k].merge(v, _merge_create_to_read, mm_param.Merge_Level_Root)

        else:
            parameters[k] = v

    return parameters


def _merge_update_params(update, read, parameters):
    for k, v in update.items():

        if k in read:
            read[k].merge(v, _merge_update_to_cr, mm_param.Merge_Level_Root)

        elif k in parameters:
            parameters[k].merge(v, _merge_update_to_create,
                                mm_param.Merge_Level_Root)

        else:
            parameters[k] = v


def _merge_create_to_read(pc, pr, level):
    if pc and pr:
        pr.set_item("required", pc.get_item("required"))
        pr.set_item("description", pc.get_item("description"))
        pr.path.update(pc.path)


def _merge_update_to_cr(pu, pcr, level):
    if pu and pcr:
        pcr.path.update(pu.path)


def _merge_update_to_create(pu, pc, level):
    if pu and pc:
        pc.path.update(pu.path)

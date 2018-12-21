import mm_param


def build_resource_params(api_info, all_models):

    create, update, read = _build_params(api_info, all_models)

    print("------ start to merge create parameters to get ------")
    parameters = _merge_create_params(create, read)

    if update:
        print("------ start to merge update parameters to get ------")
        _merge_update_params(update, read, parameters)

    read.update(parameters)

    return read


def _set_property(p, t, kv={}):
    for k, v in kv.items():
        p.set_item(k, v)

    m = {"c": "create", "u": "update", "r": "read"}
    p.set_item("field", "%s:%s" % (m[t], p.get_item("name")))


def _build_params(api_info, all_models):

    read = mm_param.build(api_info["get"]["body"], all_models)
    for v in read.values():
        v.traverse(lambda n: _set_property(n, "r", {"required": None}))

    create = mm_param.build(api_info["create"]["body"], all_models)
    for v in create.values():
        v.traverse(lambda n: _set_property(n, 'c'))

    update = None
    if "update" in api_info:
        update = mm_param.build(api_info["update"]["body"], all_models)
        for k, v in update.items():
            v.traverse(
                lambda n: _set_property(n, "u", {"required": None}))

    return create, update, read


def _merge_create_params(create, read):
    parameters = {}
    for k, v in create.items():

        if k in read:
            read[k].merge(v, _merge_create_to_get, mm_param.Merge_Level_Root)

        else:
            parameters[k] = v

    return parameters


def _merge_update_params(update, read, parameters):
    for k, v in update.items():

        if k in read:
            read[k].merge(v, _merge_update_to_get, mm_param.Merge_Level_Root)

        elif k in parameters:
            parameters[k].merge(v, _merge_update_to_create,
                                mm_param.Merge_Level_Root)

        else:
            parameters[k] = v


def _merge_create_to_get(pc, pg, level):
    if pc and pg:
        pg.set_item("required", pc.get_item("required"))
        pg.set_item("description", pc.get_item("description"))
        pg.set_item("field", "create:%s" % pc.get_item("field")["create"])


def _merge_update_to_get(pu, pcg, level):
    if pu and pcg:

        if pcg.get_item("crud") == 'r':
            pcg.set_item("description", pu.get_item("description"))

        pcg.set_item("field", "update:%s" % pu.get_item("field")["update"])


def _merge_update_to_create(pu, pc, level):
    if pu and pc:
        pc.set_item("field", "update:%s" % pu.get_item("field")["update"])

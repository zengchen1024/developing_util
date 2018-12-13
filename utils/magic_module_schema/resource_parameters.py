import mm_param


def build_resource_params(api_info, all_models):
    properties = mm_param.build(api_info["get"]["body"], all_models)
    for _, v in properties.items():
        v.traverse(lambda n: _set_property(n, {"crud": "r", "required": None}))

    print("------ start to merge create parameters to get ------")
    r = mm_param.build(api_info["create"]["body"], all_models)
    parameters = {}
    for k, v in r.items():
        v.traverse(lambda n: n.set_item("crud", 'c'))
        if k in properties:
            properties[k].merge(v, _merge_create_to_get,
                                mm_param.Merge_Level_Root)
        else:
            v.set_item("input", True)
            parameters[k] = v

    if "update" in api_info:
        print("------ start to merge update parameters to get ------")
        r = mm_param.build(api_info["update"]["body"], all_models)
        for k, v in r.items():
            v.traverse(
                lambda n: _set_property(n, {"crud": "u", "required": None}))

            if k in properties:
                properties[k].merge(v, _merge_update_to_get,
                                    mm_param.Merge_Level_Root)
            elif k in parameters:
                parameters[k].merge(v, _merge_update_to_create,
                                    mm_param.Merge_Level_Root)
            else:
                parameters[k] = v

    def output(n):
        p = n.parent
        if n.get_item("crud") == 'r' and (
                p is None or p.get_item("crud") != 'r'):
            n.set_item("output", True)

    for k, v in properties.items():
        v.traverse(output)

    return properties, parameters


def _merge_create_to_get(pc, pg, level):
    if level == mm_param.Merge_Level_Root:
        # on the case, pc and pg will exist both
        # and pg is just the get parameter

        pg.set_item("crud", pg.get_item("crud") + 'c')
        pg.set_item("required", pc.get_item("required"))
        pg.set_item("description", pc.get_item("description"))

    else:
        # there are 3 cases of parameter type: c / g / cg

        # if pg is None:
        #     pc.set_item("create_update", 'c')

        # elif pc is None:
        #     pg.set_item("output", True)

        if pc and pg:
            pg.set_item("crud", pg.get_item("crud") + 'c')
            pg.set_item("required", pc.get_item("required"))
            pg.set_item("description", pc.get_item("description"))


def _merge_update_to_get(pu, pcg, level):
    if level == mm_param.Merge_Level_Root:
        # on the case, pu and pcg will exist both
        # pcg may be c, r, cr

        if pcg.get_item("crud") == 'r':
            # on this case, pcg is just the get parameter

            pcg.set_item("description", pu.get_item("description"))

        # else:
        #     on this case, pcg is both the get/create parameter

        #     pcg.set_item("create_update", 'cu')
        pcg.set_item("crud", pcg.get_item("crud") + 'u')

    else:
        # on this case,
        # there are 7 cases of parameter type: c / u / r / cu / ur / cr / cur
        # pcg has two cases:
        #  1. pcg is one of parameter set of get
        #  2. pcg is one of parameter set of create/get

        # if pcg is None:
        #     pu.set_item("crud", 'u')

        # elif pu is None:
        #     on this case pcg may be c / r / cr

        #     if pcg.get_item("create_update") is None:
        #         this should be case 1 and part of case 2
        #         it means only get parameter shoud set output

        #         pcg.set_item("output", True)

        if pu and pcg:
            # on this case pcg may be c / r / cr
            # there are 3 cases of parameter type finally: cu / ur / cur

            if pcg.get_item("crud") == 'r':
                # it is the case of ur

                pcg.set_item("description", pu.get_item("description"))

            # else:
            #     it is the case of cu or cur
            #     pcg.set_item("create_update", 'cu')
            pcg.set_item("crud", pcg.get_item("crud") + 'u')


def _merge_update_to_create(pu, pc, level):
    if level == mm_param.Merge_Level_Root:
        pc.set_item("crud", pc.get_item("crud") + 'u')
    else:
        # if pc is None:
        #     pu.set_item("create_update", "u")

        # elif pu is None:
        #     pc.set_item("create_update", "c")
        if pu and pc:
            pc.set_item("crud", pc.get_item("crud") + 'u')


def _set_property(p, kv):
    for k, v in kv.items():
        p.set_item(k, v)

import functools
import os
import re
import sys
import yaml

from convert_word_doc import word_to_params
import mm_param


def run(doc_dir, output):

    def _generate_yaml(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            r.extend(v.to_yaml(n))
        return r

    if doc_dir[-1] != "/":
        doc_dir += "/"

    properties, parameters = build_mm_params(doc_dir)

    _change_by_config(doc_dir, parameters, properties)

    yaml_str = []
    indent = 4
    if parameters:
        yaml_str.append("%sparameters:\n" % (' ' * indent))
        yaml_str.extend(_generate_yaml(parameters, indent + 2))

    yaml_str.append("\n%sproperties:\n" % (' ' * indent))
    yaml_str.extend(_generate_yaml(properties, indent + 2))

    try:
        with open(output, "w") as o:
            o.writelines(yaml_str)
    except Exception as ex:
        print("Write schema result failed, %s" % ex)


def build_mm_params(doc_dir):

    structs = word_to_params(doc_dir + "get.docx")
    struct = structs.get('get_rsp')
    if struct is None:
        raise Exception(
            "The struct name of get response should be \'get_rsp\'")
    properties = mm_param.build(struct, structs)
    for _, v in properties.items():
        v.traverse(lambda n: n.set_item("output", True))

    f = doc_dir + "create_rsp.docx"
    if os.path.exists(f):
        structs = word_to_params(f)
        struct = structs.get("create_rsp")
        if struct is None:
            raise Exception(
                "The struct name of create response should be \'create_rsp\'")
        create_rsp = mm_param.build(struct, structs)
        for k, v in create_rsp.items():
            if k not in properties:
                v.set_item("output", True)
                properties[k] = v
            # check the items with same key

    f = doc_dir + "update_rsp.docx"
    if os.path.exists(f):
        structs = word_to_params(f)
        struct = structs.get("update_rsp")
        if struct is None:
            raise Exception(
                "The struct name of update response should be \'update_rsp\'")
        update_rsp = mm_param.build(struct, structs)
        for k, v in update_rsp.items():
            if k not in properties:
                v.set_item("output", True)
                properties[k] = v
            # check the items with same key

    structs = word_to_params(doc_dir + "create.docx")
    struct = structs.get("CreateOpts")
    if struct is None:
        raise Exception(
            "The struct name of create request should be \'create\'")
    print("------ start to merge create parameters to get ------")
    r = mm_param.build(struct, structs)
    parameters = {}
    for k, v in r.items():
        v.traverse(lambda n: n.set_item("create_update", 'c'))
        if k in properties:
            properties[k].merge(v, _merge_create_to_get,
                                mm_param.Merge_Level_Root)
        else:
            v.set_item("input", True)
            parameters[k] = v

    f = doc_dir + "update.docx"
    if os.path.exists(f):
        structs = word_to_params(f)
        struct = structs.get("UpdateOpts")
        if struct is None:
            raise Exception(
                "The struct name of update request should be \'update\'")
        print("------ start to merge update parameters to get ------")
        r = mm_param.build(struct, structs)
        for k, v in r.items():
            v.traverse(lambda n: n.set_item("create_update", 'u'))
            if k in properties:
                properties[k].merge(v, _merge_update_to_get,
                                    mm_param.Merge_Level_Root)
            elif k in parameters:
                parameters[k].merge(v, _merge_update_to_create,
                                    mm_param.Merge_Level_Root)
            else:
                parameters[k] = v

    return properties, parameters


def _merge_create_to_get(pc, pg, level):
    if level == mm_param.Merge_Level_Root:
        # on the case, pc and pg will exist both
        # and pg is just the get parameter

        pg.set_item("output", None)
        pg.set_item("create_update", 'c')
        pg.set_item("required", pc.get_item("required"))
        pg.set_item("description", pc.get_item("description"))

    else:
        # there are 3 cases of parameter type: c / g / cg

        # if pg is None:
        #     pc.set_item("create_update", 'c')

        # elif pc is None:
        #     pg.set_item("output", True)

        if pc and pg:
            pg.set_item("create_update", 'c')
            pg.set_item("required", pc.get_item("required"))
            pg.set_item("description", pc.get_item("description"))


def _merge_update_to_get(pu, pcg, level):
    if level == mm_param.Merge_Level_Root:
        # on the case, pu and pcg will exist both

        if pcg.get_item("create_update") is None:
            # on this case, pcg is just the get parameter

            pcg.set_item("output", None)
            pcg.set_item("create_update", 'u')
            pcg.set_item("description", pu.get_item("description"))

        else:
            # on this case, pcg is both the get/create parameter

            pcg.set_item("create_update", 'cu')

    else:
        # on this case,
        # there are 7 cases of parameter type: c / u / g / cu / ug / cg / cug
        # pcg has two cases:
        #  1. pcg is one of parameter set of get
        #  2. pcg is one of parameter set of create/get

        # if pcg is None:
        #     pu.set_item("create_update", 'u')

        # elif pu is None:
        #     on this case pcg may be c / g / cg

        #     if pcg.get_item("create_update") is None:
        #         this should be case 1 and part of case 2
        #         it means only get parameter shoud set output

        #         pcg.set_item("output", True)

        if pu and pcg:
            # on this case pcg may be c / g / cg
            # there are 3 cases of parameter type finally: cu / ug / cug

            if pcg.get_item("create_update") is None:
                # it is the case of ug

                pcg.set_item("create_update", 'u')
                pcg.set_item("description", pu.get_item("description"))

            else:
                # it is the case of cu or cug
                pcg.set_item("create_update", 'cu')


def _merge_update_to_create(pu, pc, level):
    if level == mm_param.Merge_Level_Root:
        pc.set_item("create_update", "cu")
    else:
        # if pc is None:
        #     pu.set_item("create_update", "u")

        # elif pu is None:
        #     pc.set_item("create_update", "c")
        if pu and pc:
            pc.set_item("create_update", "cu")


def _change_by_config(doc_dir, parameters, properties):

    def _find_param(k):
        keys = k.split('.')

        k0 = keys[0]
        obj = properties.get(k0)
        if obj is None:
            obj = parameters.get(k0)
            if obj is None:
                print("Can not find the head parameter(%s)" % k0)
                return None, ''

        n = len(keys)
        try:
            for i in range(1, n):
                obj = getattr(obj, keys[i])
        except AttributeError:
            print("Can not find the parameter(%s)" % keys[i])
            return None, ''

        return obj, keys[-1]

    def _config_name(p, pn, v):
        p.set_item("name", v)
        # it shoud check first because it may conflict with 'field' config
        if p.get_item("field") is None:
            p.set_item("field", pn)

    def _config_values(p, pn, v):
        if not isinstance(p, mm_param.MMEnum):
            print("Can not set values for a non enum(%s) parameter(%s)" %
                  (type(p), pn))
        else:
            p.set_item("values", map(str.strip, v.strip(', ').split(',')))

    def _config_element_type(p, pn, v):
        if not isinstance(p, mm_param.MMEnum):
            print("Can not set values for a non enum(%s) parameter(%s)" %
                  (type(p), pn))
        else:
            p.set_item("element_type", v)

    def _config_create_update(p, pn, v):
        if v not in ['c', 'u', 'cu', None]:
            print("The value of 'create_update' "
                  "should be in ['c', 'u', 'cu', None]")
            return
        p.set_item('create_update', v)

    f = doc_dir + "api_cnf.yaml"
    if not os.path.exists(f):
        print("The path(%s) is not correct" % f)
        return

    cnf = None
    with open(f, 'r') as stream:
        try:
            cnf = yaml.load(stream)
        except Exception as ex:
            raise Exception("Read %s failed, err=%s" % (f, ex))
    if cnf is None:
        return

    fields = {}

    fm = {
        'name': _config_name,
        'is_id': lambda p, pn, v: p.set_item("is_id", True),
        'create_update': _config_create_update,
        'values': _config_values,
        'element_type': _config_element_type,
        'exclude': lambda p, pn, v: p.set_item("exclude", True),
        'field': lambda p, pn, v: p.set_item("field", v),
    }
    for p, kv in cnf.items():
        if not p:
            continue
        p = p.strip()
        obj, pn = _find_param(p)
        if not obj:
            continue
        for k, v in kv.items():
            if k in fm:
                fm[k](obj, pn, v)
                if k == 'field':
                    fields[p] = v
            else:
                print("Config unknown property(%s) for "
                      "parameter(%s)" % (k, pn))

    def _replace_desc(p, old, new):
        desc = p.get_item("description")
        pt = re.compile("\\b%s\\b" % old)
        if re.findall(pt, desc):
            p.set_item("description", re.sub(pt, new, desc))

    for p, new in fields.items():
        if new == "name":  # 'name' is not a specical parameter, ignore it.
            continue

        i = p.rfind('.')
        if i > 0:
            obj, pn = _find_param(p[:i])
            if not obj:
                continue
            f = functools.partial(_replace_desc, old=p[i+1:], new=new)
            obj.traverse(f)
        else:
            f = functools.partial(_replace_desc, old=p, new=new)
            for _, obj in parameters.items():
                obj.traverse(f)

            for _, obj in properties.items():
                obj.traverse(f)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Input docx dir and output file")
    else:
        run(*sys.argv[1:])

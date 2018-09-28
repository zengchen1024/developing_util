import functools
import os
import re
import sys
import yaml

from convert_word_doc import word_to_params
import mm_param


def run(doc_dir, output):

    def _generate_schema(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            r.extend(v.to_schema(n))
        return r

    if doc_dir[-1] != "/":
        doc_dir += "/"

    properties, parameters = build_mm_params(doc_dir)

    _change_by_config(doc_dir, parameters, properties)

    if parameters:
        properties.update(parameters)

    yaml_str = []
    i = 2
    #yaml_str.append("\n%sSchema: map[string]*schema.Schema{\n" % ('\t' * i))
    yaml_str.extend(_generate_schema(properties, i + 1))
    yaml_str[-1] = yaml_str[-1][:-1]
    yaml_str.append("%s},\n" % ('\t' * i))

    o = None
    try:
        o = open(output, "a")
        o.writelines(yaml_str)
    except Exception as ex:
        print("Write schema result failed, %s" % ex)
    finally:
        if o:
            o.close()


def build_mm_params(doc_dir):

    structs = word_to_params(doc_dir + "get.docx")
    struct = structs.get('get_rsp')
    if struct is None:
        raise Exception(
            "The struct name of get response should be \'get_rsp\'")
    properties = mm_param.build(struct, structs)
    for _, v in properties.items():
        v.set_item("Computed", True)

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
                v.set_item("Computed", True)
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
                v.set_item("Computed", True)
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
        v.set_item("create_update", 'c')
        if k in properties:
            properties[k].merge(v, _create_merge_to_get)
        else:
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
            v.set_item("create_update", 'u')
            if k in properties:
                properties[k].merge(v, _update_merge_to_get)
            else:
                parameters[k] = v

    return properties, parameters


def _create_merge_to_get(pc, pg):
    if pc is None:
        pg.set_item("Computed", True)
    elif pc and pg:
        if pc.get_item("Required"):
            pg.set_item("Computed", None)
        pg.set_item("Required", pc.get_item("Required"))
        pg.set_item("description", pc.get_item("description"))
        # only the top layer should set this config
        if pc.get_item("create_update") is not None:
            pg.set_item("create_update", 'c')


def _update_merge_to_get(pu, pg):
    if pu is None:
        pg.set_item("Computed", True)
    elif pu and pg:
        pg.set_item("Computed", None)
        # only the top layer should set this config
        if pu.get_item("create_update") is not None:
            cu = pg.get_item("create_update")
            if cu is None:
                cu = ''
            cu += 'u'
            pg.set_item("create_update", cu)


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
        except AttributeError as ex:
            print("Can not find the parameter(%s)" % keys[i])
            return None, ''

        return obj, keys[-1]

    def _config_fields(p, pn, v):
        p.set_item("field", pn)
        p.set_item("name", v)

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
        'field': _config_fields,
        'is_id': lambda p, pn, v: p.set_item("is_id", True),
        'create_update': _config_create_update,
        'values': _config_values,
        'element_type': _config_element_type,
        'exclude': lambda p, pn, v: p.set_item("exclude", True),
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
        if new == "name": # 'name' is not a specical parameter, ignore it.
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

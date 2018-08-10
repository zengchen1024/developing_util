import os
import sys
import yaml

from convert_word_doc import word_to_params
import mm_param


def run(resource_name, doc_dir, output):

    def _generate_yaml(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            r.extend(v.to_yaml(n))
        return r

    if doc_dir[-1] != "/":
        doc_dir += "/"

    properties, parameters = build_mm_params(resource_name, doc_dir)

    _change_by_config(doc_dir, parameters, properties)

    yaml_str = []
    indent = 4
    if parameters:
        yaml_str.append("%sparameters:\n" % (' ' * indent))
        yaml_str = _generate_yaml(parameters, indent + 2)

    yaml_str.append("\n%sproperties:\n" % (' ' * indent))
    yaml_str.extend(_generate_yaml(properties, indent + 2))

    try:
        o = open(output, "w")
        o.writelines(yaml_str)
    except Exception as ex:
        print("Write schema result failed, %s" % ex)
    finally:
        if o:
            o.close()


def build_mm_params(resource_name, doc_dir):

    structs = word_to_params(doc_dir + "get.docx")
    struct = structs.get(resource_name)
    if struct is None:
        raise Exception(
            "The struct name of get response should be \'get_rsp\'")
    properties = mm_param.build(struct, structs)
    for _, v in properties.items():
        v.set_item("output", True)

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
    r = mm_param.build(struct, structs)
    parameters = {}
    for k, v in r.items():
        v.set_item("create_update", 'c')
        if k in properties:
            properties[k].merge(v, _create_merge_to_get)
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
        pg.set_item("output", True)
    elif pc and pg:
        pg.set_item("output", None)
        pg.set_item("required", pc.get_item("required"))
        pg.set_item("description", pc.get_item("description"))
        # only the top layer should set this config
        if pc.get_item("create_update") is not None:
            pg.set_item("create_update", 'c')


def _update_merge_to_get(pu, pg):
    if pu is None:
        pg.set_item("output", True)
    elif pu and pg:
        pg.set_item("output", None)
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

    for k, v in cnf.get('fields', {}).items():
        if not k:
            continue
        obj, pn = _find_param(k)
        if obj:
            obj.set_item("field", pn)
            obj.set_item("name", v)

    for k, v in cnf.get('enum_values', {}).items():
        if not k:
            continue
        obj, pn = _find_param(k)
        if not obj:
            continue
        if not isinstance(obj, mm_param.MMEnum):
            print("Can not set values for a non enum(%s) parameter(%s)" %
                  (type(obj), pn))
            continue

        obj.set_item("values", map(str.strip, v.strip(', ').split(',')))

    rid = cnf.get("resource_id")
    if rid:
        obj, _ = _find_param(rid)
        if obj:
            obj.set_item("is_id", True)

    cu = "create_update"
    for i in cnf.get('exclude_create', []):
        obj, _ = _find_param(i)
        if obj:
            obj.set_item(
                cu, 'u' if obj.get_item(cu, '').find('u') >= 0 else None)

    for k, v in cnf.get('enum_element_type', {}).items():
        obj, _ = _find_param(k)
        if obj:
            obj.set_item("element_type", v)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Input resource name, docx dir and output file")
    else:
        run(*sys.argv[1:])

import os
import sys

from convert_word_doc import word_to_params
import mm_param


def run(doc_dir, output):

    def _generate_yaml(parameters, indent):
        r = []
        keys = parameters.keys().sort()
        for k in keys:
            v = parameters[k]
            r.extend(v.to_yaml(indent))
        return r

    properties, parameters = build_mm_params(doc_dir)

    yaml_str = []
    indent = 4
    if parameters:
        yaml_str.append("%sparameters:\n" % (' ' * indent))
        yaml_str.extend(_generate_yaml(parameters, indent + 2))

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


def build_mm_params(doc_dir):
    if doc_dir[-1] != "/":
        doc_dir += "/"

    structs = word_to_params(doc_dir + "get.docx")
    struct = structs.get("get_rsp")
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
    struct = structs.get("create")
    if struct is None:
        raise Exception(
            "The struct name of create request should be \'create\'")
    r = mm_param.build(struct, structs)
    parameters = {}
    for k, v in r.items():
        v.set_item("create_update", 'c')
        if k in properties:
            properties[k].merge(v, _create_merge_get)
        else:
            v.set_item("input", True)
            parameters[k] = v

    f = doc_dir + "update.docx"
    if os.path.exists(f):
        structs = word_to_params(f)
        struct = structs.get("update")
        if struct is None:
            raise Exception(
                "The struct name of update request should be \'update\'")
        r = mm_param.build(struct, structs)
        for k, v in r.items():
            v.set_item("update_update", 'u')
            if k in properties:
                properties[k].merge(v, _update_merge_get)
            else:
                parameters[k] = v


def _create_merge_get(pc, pg):
    if pc is None:
        pg.set_item("output", None)
    elif pc and pg:
        pg.set_item("output", None)
        pg.set_item("required", pg.get_item("required"))
        pg.set_item("create_update", 'c')


def _update_merge_get(pu, pg):
    if pu is None:
        pg.set_item("output", None)
    elif pu and pg:
        pg.set_item("output", None)
        cu = pg.get_item("create_update")
        if cu is None:
            cu = ''
        cu += 'u'
        pg.set_item("create_update", cu)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Input docx dir and output file")
    else:
        run(*sys.argv)

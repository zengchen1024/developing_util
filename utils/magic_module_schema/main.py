import functools
import os
import re
import sys
import yaml

#from convert_word_doc import word_to_params
import mm_param


def run(doc_dir, output, tag="alarm"):

    def _generate_yaml(params, n):
        r = []
        keys = sorted(params.keys())
        for k in keys:
            v = params[k]
            r.extend(v.to_yaml(n))
        return r

    if doc_dir[-1] != "/":
        doc_dir += "/"

    api_yaml, model_yaml= build_mm_params1(doc_dir)
    all_api = classify_by_api(api_yaml, model_yaml, tag)

    properties, parameters = build_mm_params(all_api, model_yaml)
    #_change_by_config(doc_dir, parameters, properties)

    yaml_str = []
    indent = 4
    if parameters:
        yaml_str.append("%sparameters:\n" % (' ' * indent))
        yaml_str.extend(_generate_yaml(parameters, indent + 2))

    yaml_str.append("\n%sproperties:\n" % (' ' * indent))
    yaml_str.extend(_generate_yaml(properties, indent + 2))

    create_api = all_api["create"]["api"]
    h = ""
    with open("template/resource.yaml", "r") as o:
        h = o.readlines()
    msg_prefix = [""]
    for i in ["create", "update", "get", "list"]:
        s = all_api.get(i, {}).get("msg_prefix", None)
        if s:
            msg_prefix.append("%s: \"%s\"" % (i, s))
    if len(msg_prefix) == 1:
        msg_prefix = []

    h = [
        "".join(h).replace("{{", "{"). replace("}}", "}").format(**{
            "name": tag[0].upper() + tag[1:].lower(),
            "service_type": create_api["service_type"],
            "base_url": create_api["path"],
            "list_url": "",
            "msg_prefix": "\n      ".join(msg_prefix),
            "description": ""
        })
    ]
    h.extend(yaml_str)

    write_strs(output, h)


def write_strs(output, strs):
    with open(output, "w") as o:
        try:
            o.writelines(strs)
        except Exception as ex:
            try:
                o.writelines(map(lambda s: s.encode("utf-8"), strs))
            except Exception as ex:
                print("Write schema result failed, %s" % ex)


def build_mm_params1(doc_dir):

    def read_yaml(f):
        with open(f, 'r') as stream:
            try:
                return yaml.load(stream)
            except Exception as ex:
                raise Exception("Read %s failed, err=%s" % (f, ex))

    api_yaml = read_yaml(doc_dir + "api.yaml")
    model_yaml = read_yaml(doc_dir + "models.yaml")
    return api_yaml, model_yaml


def classify_by_api(api_yaml, model_yaml, tag):
    r = []
    for k, v in api_yaml.items():
        if v.get("tag", "") == tag:
            path = v["path"]
            if path[-1] != "/":
                path += "/"
            r.append((path, v["method"].lower(), k))

    def _cmp(x, y):
        if x[0] != y[0]:
            return len(x[0]) - len(y[0])

        m = {
            "post": 1,
            "put": 2,
        }
        return m.get(x[1], 3) - m.get(y[1], 3)

    r1 = sorted(r, _cmp)
    if r1[0][1] not in ["post", "put"]:
        raise Exception("It can not find the create api")

    def _build_create_info():
        api = api_yaml[r1[0][2]]
        p = api.get("request_body", {}).get("datatype", "")
        if p not in model_yaml:
            raise Exception("It can not build create parameter, "
                            "the datatype(%s) is not a struct" % p)

        msg_prefix = None
        body = model_yaml.get(p)
        p = body
        if len(p) == 1 and p[0]["datatype"] in model_yaml:
            msg_prefix = p[0]["name"]
            body = model_yaml[p[0]["datatype"]]

        return {
            "api": api,
            "msg_prefix": msg_prefix,
            "body": body
        }

    def _find_rud_api(t, methods):
        create_path = r1[0][0]
        s = len(create_path)
        for item in r1:
            if item[1] not in methods:
                continue

            path = item[0]
            if len(path) > s and re.match(r"^{[A-Za-z_0-9]+}/$", path[s:]):
                return api_yaml[item[2]]
                break
        else:
            raise Exception("It can not to find the (%s) api" % t)

    def _build_get_info():
        api = _find_rud_api("get", ["get"])
        p = api.get("response", {}).get("datatype", "")
        if p not in model_yaml:
            raise Exception("It can not build get parameter, "
                            "the datatype(%s) is not a struct" % p)

        msg_prefix = None
        body = model_yaml.get(p)
        p = body
        if len(p) == 1 and p[0]["datatype"] in model_yaml:
            msg_prefix = p[0]["name"]
            body = model_yaml[p[0]["datatype"]]

        return {
            "api": api,
            "msg_prefix": msg_prefix,
            "body": body
        }

    def _build_update_info():
        api = _find_rud_api("update", ["post", "put", "patch"])
        p = api.get("request_body", {}).get("datatype", "")
        if p not in model_yaml:
            raise Exception("It can not build update parameter, "
                            "the datatype(%s) is not a struct" % p)

        msg_prefix = None
        body = model_yaml.get(p)
        p = body
        if len(p) == 1 and p[0]["datatype"] in model_yaml:
            msg_prefix = p[0]["name"]
            body = model_yaml[p[0]["datatype"]]

        return {
            "api": api,
            "msg_prefix": msg_prefix,
            "body": body
        }

    r = {
        "create": _build_create_info(),
        "get": _build_get_info(),
    }
    _find_rud_api("delete", ["delete"])
    try:
        v = _build_update_info()
        r["update"] = v
    except Exception as ex:
        print(str(ex))

    return r


def build_mm_params(all_api, all_models):
    properties = mm_param.build(all_api["get"]["body"], all_models)
    for _, v in properties.items():
        v.traverse(lambda n: n.set_item("crud", "r"))

    print("------ start to merge create parameters to get ------")
    r = mm_param.build(all_api["create"]["body"], all_models)
    parameters = {}
    for k, v in r.items():
        v.traverse(lambda n: n.set_item("crud", 'c'))
        if k in properties:
            properties[k].merge(v, _merge_create_to_get,
                                mm_param.Merge_Level_Root)
        else:
            v.set_item("input", True)
            parameters[k] = v

    if "update" in all_api:
        print("------ start to merge update parameters to get ------")
        r = mm_param.build(all_api["update"]["body"], all_models)
        for k, v in r.items():
            v.traverse(lambda n: n.set_item("crud", 'u'))
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
                if k == 'name':
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

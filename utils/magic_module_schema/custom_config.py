import functools
import os
import re

import mm_param
import utils


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


def _find_param(parameters, properties, k):
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


def _replace_description(fields, parameters, properties):

    def _replace_desc(p, old, new):
        desc = p.get_item("description")
        pt = re.compile("\\b%s\\b" % old)
        if re.findall(pt, desc):
            p.set_item("description", re.sub(pt, new, desc))

    find_param = functools.partial(_find_param, parameters=parameters,
                                   properties=properties)

    for p, new in fields.items():
        if new == "name":  # 'name' is not a specical parameter, ignore it.
            continue

        i = p.rfind('.')
        if i > 0:
            obj, pn = find_param(p[:i])
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


def _config_list_op(cnf, api_info, fields):
    list_op = cnf["list_op"]

    identity = list_op.get("identity", None)
    if not identity:
        raise Exception("Must set (identity) in list_op")

    obj = api_info["list"]
    if fields:
        obj["identity"] = [
            fields.get(i, i) for i in identity
        ]

        for i in obj["api"]["query_params"]:
            if i["name"] in fields:
                i["name"] = fields[i["name"]]
    else:
        obj["identity"] = identity


def _replace_path_params(api_info, fields):
    for _, v in api_info.items():
        for i in v["api"].get("path_params", []):
            if i["name"] in fields:
                i["name"] = fields[i["name"]]


def custom_config(cnf, parameters, properties, api_info):
    fields = {}
    find_param = functools.partial(_find_param, parameters=parameters,
                                   properties=properties)
    fm = {
        'name': _config_name,
        'is_id': lambda p, pn, v: p.set_item("is_id", True),
        'create_update': _config_create_update,
        'values': _config_values,
        'element_type': _config_element_type,
        'exclude': lambda p, pn, v: p.set_item("exclude", True),
        'field': lambda p, pn, v: p.set_item("field", v),
    }
    for p, kv in cnf.get("properties", {}).items():
        if not p:
            continue

        p = p.strip()
        obj, pn = find_param(p)
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

    if fields:
        _replace_description(fields, parameters, properties)
        _replace_path_params(api_info, fields)

    if "list_op" in cnf:
        _config_list_op(cnf, api_info, fields)

import functools
import re

import mm_param


class RootNode(object):
    def __init__(self, parameters):
        self._p = parameters
        for v in parameters.values():
            v.parent = self

    def child(self, key):
        if key in self._p:
            return self._p[key]

        raise Exception("no child with key(%s)" % key)

    def add_child(self, child):
        self._p[child.api_name] = child

    def find_param(self, keys):
        obj = self
        for k in keys.split('.'):
            obj = obj.child(k.strip())

        return obj

    def add_parameter(self, argv):
        v = argv.split(" ")
        name = v[0]
        items = v[1:]
        cmd = "add %s" % argv

        node_name = name
        parent = self
        i = name.rfind(":")
        if i > 0:
            parent = self.find_param(name[:i])
            node_name = name[(i+1):]
        else:
            if name in self._p:
                raise Exception("Execute cmd(%s) failed, the "
                                "parameter(%s) is exist" % (cmd, name))

        p = {}
        crud = []
        t = set()
        for item in items:
            i = item.find(":")
            if i == -1:
                raise Exception("Execute cmd(%s) failed, the "
                                "parameter should be in format of k:v where "
                                "k is one of create, update, read and v is "
                                "the index to the real parameter" % cmd)

            op = item[:i]
            if op not in ["create", "upate", "read"]:
                raise Exception("Execute cmd(%s) failed, the operation "
                                "must be crate, update or read" % cmd)

            o = self.find_param(item[(i + 1):])
            p[op] = o
            crud.append(op[0])
            t.add(type(o))

        if len(t) != 1:
            raise Exception("Execute cmd(%s) failed, all the "
                            "parameter should be the same type" % cmd)

        obj = p.values()[0].clone()
        obj.api_name = node_name
        obj.parent = parent
        obj.set_item("name", node_name)
        obj.set_item("crud", "".join(crud))
        if crud == "r":
            obj.set_item("output", True)

        parent.add_child(obj)

        if "create" in p:
            o = p["create"]

            v = o.get_item("required")
            if v:
                obj.set_item("required", v)

            v = o.get_item("description")
            if v:
                obj.set_item("description", v)
                return

        if "update" in p:
            v = p["update"].get_item("description")
            if v:
                obj.set_item("description", v)
                return

        if "read" in p:
            v = p["read"].get_item("description")
            if v:
                obj.set_item("description", v)

    def rename(self, argv):
        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("Execute cmd(rename %s) failed, must input "
                            "node and its new name" % argv)

        p = self.find_param(v[0])
        p.set_item("name", v[1])

    def delete(self, node):
        p = self.find_param(node)
        p.set_item("exclude", True)


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


def _find_param(parameters, k):
    keys = k.split('.')
    k0 = keys[0]
    obj = parameters.get(k0)
    if obj is None:
        raise Exception("Can not find the head parameter(%s)" % k0)

    try:
        for k in keys[1:]:
            obj = getattr(obj, k)

    except AttributeError:
        raise Exception("Can not find the parameter(%s)" % k)

    return parameters if obj.parent is None else obj.parent, obj, keys[-1]


def _replace_description(fields, parameters, properties):

    def _replace_desc(p, old, new):
        desc = p.get_item("description")
        pt = re.compile("\\b%s\\b" % old)
        if re.findall(pt, desc):
            p.set_item("description", re.sub(pt, new, desc))

    find_param = functools.partial(_find_param, parameters, properties)

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
    rn = RootNode(parameters)
    fm = {
        'rename': rn.rename,
        'delete': rn.delete,
        'add': rn.add_parameter,
    }

    for cmds in cnf.get("adjust", []):
        if isinstance(cmds, str):
            cmds = [cmds]

        for cmd in cmds:
            print cmd

            i = cmd.find(" ")
            f = fm.get(cmd[:i])
            if not f:
                raise Exception("Execute cmd(%s) failed, "
                                "unknown cmd(%s)" % (cmd, cmd[:i]))

            f(cmd[(i + 1):])
            print "  done"

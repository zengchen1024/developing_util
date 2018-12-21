import functools
import re

from common import mm_param


class _Tree(object):
    def __init__(self, properties):
        self._p = properties

        for v in self._p.values():
            v.parent = self

    def child(self, key):
        if key in self._p:
            return self._p[key]

        raise Exception("no child with key(%s)" % key)

    def add_child(self, child):
        self._p[child.get_item("name")] = child

    def delete_child(self, child):
        self._p.pop(child.get_item("name"))

    def find_param(self, keys):
        obj = self
        for k in keys.split('.'):
            obj = obj.child(k.strip())

        return obj

    def rename(self, argv):
        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("Execute cmd(rename %s) failed, must input "
                            "node and its new name" % argv)

        p = self.find_param(v[0])
        p.set_item("name", v[1])

    def delete(self, node):
        p = self.find_param(node)
        p.parent.delete_child(p)

    def append_parameter(self, argv):
        v = argv.split(" ")
        name = v[0]
        items = v[1:]
        cmd = "append %s" % argv

        parent = self.find_param(name)

        p = []
        t = set()
        t.add(type(parent))
        for item in items:
            o = self.find_param(item)
            p.append(o)
            t.add(type(o))

        if len(t) != 1:
            raise Exception("Execute cmd(%s) failed, all the "
                            "parameter should be the same type" % cmd)

        crud = [i for i in parent.get_item("crud")]
        for o in p:
            for i in o.get_item("crud"):
                if i in crud:
                    raise Exception("Execute cmd(%s) failed, the parameter "
                                    "members have same crud" % cmd)
                crud.append(i)

        self._add_members(parent, p)

    def add_parameter(self, argv):
        v = argv.split(" ")
        name = v[0]
        items = v[1:]
        cmd = "add %s" % argv

        node_name = name
        parent = self
        i = name.rfind(".")
        if i > 0:
            parent = self.find_param(name[:i])
            node_name = name[(i+1):]

        try:
            parent.child(node_name)
            n = "root_node" if parent == self else parent.get_item("name")
            raise Exception("Execute cmd(%s) failed, the parameter(%s) is "
                            "exist in parameter(%s)" % (cmd, node_name, n))
        except:
            pass

        p = []
        t = set()
        for item in items:
            o = self.find_param(item)
            p.append(o)
            t.add(type(o))

        if len(t) != 1:
            raise Exception("Execute cmd(%s) failed, all the "
                            "parameter should be the same type" % cmd)

        crud = []
        for o in p:
            for i in o.get_item("crud"):
                if i in crud:
                    raise Exception("Execute cmd(%s) failed, the parameter "
                                    "members have same crud" % cmd)
                crud.append(i)

        obj = p[0].clone()
        obj.parent = parent
        obj.set_item("name", node_name)
        parent.add_child(obj)

        self._add_members(obj, p)

    def _add_members(self, obj, members):
        for o in members:
            field = [
                "%s:%s" % (k, v) for k, v in o.get_item("field").items() if v
            ]
            obj.set_item("field", " ".join(field))

            crud = o.get_item("crud")
            if crud.find("c") != -1:
                v = o.get_item("required")
                if v:
                    obj.set_item("required", v)

                v = o.get_item("description")
                if v:
                    obj.set_item("description", v)

            if obj.get_item("description"):
                continue

            if crud.find("u") != -1:
                v = o.get_item("description")
                if v:
                    obj.set_item("description", v)

            else:
                v = o.get_item("description")
                if v:
                    obj.set_item("description", v)


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


def adjust(adjust_cmds, properties):
    rn = _Tree(properties)
    fm = {
        'rename': rn.rename,
        'delete': rn.delete,
        'add': rn.add_parameter,
        'append': rn.append_parameter
    }

    for cmds in adjust_cmds:
        if isinstance(cmds, str):
            cmds = [cmds]

        for cmd in cmds:
            i = cmd.find(" ")
            f = fm.get(cmd[:i])
            if not f:
                raise Exception("Execute cmd(%s) failed, "
                                "unknown cmd(%s)" % (cmd, cmd[:i]))

            f(cmd[(i + 1):])

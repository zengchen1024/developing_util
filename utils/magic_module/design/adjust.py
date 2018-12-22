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

        obj = self.find_param(name)

        members = {path: self.find_param(path) for path in items}

        try:
            m = {name: obj}
            m.update(members)
            self._can_merge(name, obj.parent, m)
        except Exception as ex:
            raise Exception("Execute cmd(%s) failed, %s" % (cmd, ex))

        self._add_members(name, obj, members)

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
        except Exception:
            pass

        members = {path: self.find_param(path) for path in items}
        try:
            self._can_merge(name, parent, members)
        except Exception as ex:
            raise Exception("Execute cmd(%s) failed, %s" % (cmd, ex))

        obj = members.values()[0].clone()
        obj.parent = parent
        obj.set_item("name", node_name)

        self._add_members(name, obj, members)

        parent.add_child(obj)

    def _can_merge(self, node_path, parent, members):
        depth = node_path.count(".") + 1
        t = set()
        for path, o in members.items():
            t.add(type(o))
            op = o.parent

            d = path.count(".") + 1
            if d < depth:
                raise Exception("can't move the hight level node(%s) to the "
                                "low level node(%s)" % (path, node_path))

            elif d > depth:
                p = o
                for i in range(d - depth):
                    p = p.parent
                    if isinstance(p, mm_param.MMArray):
                        raise Exception("can't move the low level node(%s) "
                                        "whose ancestor is an array to hight "
                                        "level node(%s)" % (path, node_path))
                op = p.parent

            if op != parent:
                raise Exception("can't merge node(%s) to node(%s) with "
                                "different ancestor" % (path, node_path))

        if len(t) != 1:
            raise Exception("not all parameters are the same type")

        crud = []
        for o in members.values():
            for i in o.get_item("crud"):
                if i in crud:
                    raise Exception("there are same crud")
                crud.append(i)

    def _add_members(self, node_path, obj, members):
        depth = node_path.count(".") + 1
        for path, o in members.items():
            field = {}
            for k, v in o.get_item("field").items():
                if not v:
                    continue

                r = [v]
                p = o
                for i in range(path.count(".") + 1 - depth):
                    p = p.parent
                    f = p.get_item("field")[k]
                    if not f:
                        raise Exception("impossible!!, "
                                        "parent has no field(%s)" % k)
                    r.append(f)
                r.reverse()

                field[k] = ".".join(r)

            obj.set_item("field", field)

            crud = o.get_item("crud")
            if "c" in crud:
                v = o.get_item("required")
                if v:
                    obj.set_item("required", v)

                v = o.get_item("description")
                if v:
                    obj.set_item("description", v)

            if obj.get_item("description"):
                continue

            if "u" in crud:
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

import functools
import re

from common import mm_param


class _Tree(object):
    def __init__(self, properties):
        self._p = properties

        for v in self._p.values():
            v.parent = self

    @property
    def parent(self):
        return None

    def child(self, key):
        if key in self._p:
            return self._p[key]

        raise Exception("parent:root, no child with key(%s)" % key)

    def add_child(self, child):
        self._p[child.get_item("name")] = child
        child.parent = self

    def delete_child(self, child):
        self._p.pop(child.get_item("name"))

    def find_param(self, keys):
        obj = self
        for k in keys.split('.'):
            obj = obj.child(k.strip())

        return obj

    def set_property(self, argv):
        ex_msg = "Execute cmd(set %s) failed, " % argv

        v = argv.split(" ")
        if len(v) < 3:
            raise Exception("%smust input node, property and its new"
                            " value" % ex_msg)

        c = "description"
        if v[1] == c:
            v[2] = argv[argv.find(c) + len(c) + 1:]

        p = self.find_param(v[0])
        p.set_item(v[1], v[2])

    def rename(self, argv):
        ex_msg = "Execute cmd(rename %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node and its new name" % ex_msg)

        p = self.find_param(v[0])
        parent = p.parent
        try:
            self._raise_if_duplicate_name(parent, v[1])
        except Exception as ex:
            raise Exception("%s%s" % (ex_msg, ex))

        # delete old index, because the parent stores the child in map
        parent.delete_child(p)

        # rename and add node with new index
        p.set_item("name", v[1])
        parent.add_child(p)

    def delete(self, node):
        p = self.find_param(node)
        p.parent.delete_child(p)

    def move(self, argv):
        ex_msg = "Execute cmd(move %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node and new location of parent, "
                            "input root if move to first level" % ex_msg)

        parent = self if v[1] == "root" else self.find_param(v[1])

        try:
            self._raise_if_duplicate_name(parent, v[0].split(".")[-1])
        except Exception as ex:
            raise Exception("%s%s" % (ex_msg, ex))

        # must run find, delete then add. if add before delete, then there is
        # no effect, because it will be delete from new parent.
        p = self.find_param(v[0])
        p.parent.delete_child(p)
        parent.add_child(p)

    def merge_to(self, argv):
        """ merge node1 to node2 """

        ex_msg = "Execute cmd(merge_to %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node1 and node2" % ex_msg)

        src = v[0]
        target = v[1]
        self.find_param(target).merge(
            self.find_param(src), _merge_to, None)

        self.delete(src)

    def _raise_if_duplicate_name(self, parent, node_name):
        try:
            parent.child(node_name)
        except Exception:
            return

        n = "root_node" if parent == self else parent.get_item("name")

        raise Exception("the name(%s) is exist in parameter(%s)" % (
                            node_name, n))

    def add_path_param(self, create_api_id, argv):
        ex_msg = "Execute cmd(add_path_param %s) failed, " % argv

        v = argv.split(" ")
        if len(v) < 3:
            raise Exception("%smust input path parameter name, type[str, "
                            "bool, int] and description" % ex_msg)

        parent = self
        try:
            self._raise_if_duplicate_name(parent, v[1])
        except Exception as ex:
            raise Exception("%s%s" % (ex_msg, ex))

        dt = v[1]
        if dt not in ["str", "bool", "int"]:
            raise Exception("%snot support type(%s)" % (ex_msg, dt))

        name = v[0]
        p = {
            "name": name,
            "datatype": dt,
            "description": argv[argv.find(dt) + len(dt) + 1:],
            "mandatory": True
        }
        p = mm_param.build([p], None, parent)[name]
        p.path[create_api_id] = name

        parent.add_child(p)


def _merge_to(node2, node1, level):
    if not (node1 and node2):
        return

    op1 = set(node1.path.keys())
    op2 = set(node2.path.keys())
    if op1.intersection(op2):
        raise Exception("can not merge the parameter of same "
                        "api(%s)" % " ".join(op1.intersection(op2)))

    node1.path.update(node2.path)

    if node2.get_item("required"):
        node1.set_item("required", True)


def adjust(adjust_cmds, properties, create_api_id):
    rn = _Tree(properties)
    fm = {
        'rename': rn.rename,
        'delete': rn.delete,
        'merge_to': rn.merge_to,
        'move': rn.move,
        'set': rn.set_property,
        'add_path_param': functools.partial(rn.add_path_param, create_api_id)
    }

    for cmds in adjust_cmds:
        if isinstance(cmds, str):
            cmds = [cmds]

        for cmd in cmds:
            cmd = re.sub(r" +", " ", cmd)
            i = cmd.find(" ")
            f = fm.get(cmd[:i])
            if not f:
                raise Exception("Execute cmd(%s) failed, "
                                "unknown cmd(%s)" % (cmd, cmd[:i]))

            f(cmd[(i + 1):])

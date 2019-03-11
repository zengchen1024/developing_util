import re


class _Tree(object):
    def __init__(self, properties):
        self._p = properties

        for v in self._p.values():
            v.parent = self

    def child(self, key):
        if key in self._p:
            return self._p[key]

        raise Exception("parent:root, no child with key(%s)" % key)

    def add_child(self, child):
        self._p[child.get_item("name")] = child

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

        parent.add_child(self.find_param(v[0]))
        self.delete(v[0])

    def merge(self, argv):
        """ merge node1 with node2 """

        ex_msg = "Execute cmd(merge %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node1 and node2" % ex_msg)

        self.find_param(v[0]).merge(self.find_param(v[1]), _merge_to, None)

        self.delete(v[1])

    def _raise_if_duplicate_name(self, parent, node_name):
        try:
            parent.child(node_name)
        except Exception:
            return

        n = "root_node" if parent == self else parent.get_item("name")

        raise Exception("the name(%s) is exist in parameter(%s)" % (
                            node_name, n))


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


def adjust(adjust_cmds, properties):
    rn = _Tree(properties)
    fm = {
        'rename': rn.rename,
        'delete': rn.delete,
        'merge': rn.merge,
        'move': rn.move,
        'set': rn.set_property
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

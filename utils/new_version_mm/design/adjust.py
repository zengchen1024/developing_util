import functools
import re

from common import mm_param
from common.preprocess import find_parameter
from common.utils import underscore


def _node_index(n):
    return n.alias if n.alias else n.get_item("name")


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

    def add_child(self, key, child):
        self._p[key] = child
        child.parent = self

    def delete_child(self, key):
        self._p.pop(key)

    def find_param(self, keys):
        obj = self
        for k in keys.split('.'):
            obj = obj.child(k.strip())

        return obj

    def set_desc(self, argv):
        ex_msg = "Execute cmd(set_desc %s) failed, " % argv

        v = argv.split(" ")
        if len(v) < 2:
            raise Exception("%smust input node and its new desc" % ex_msg)

        self.find_param(v[0]).set_item(
            "description", argv.replace(v[0] + " ", "", 1))

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
        parent.delete_child(_node_index(p))

        # rename and add node with new index
        p.set_item("name", v[1])
        p.alias = ""
        parent.add_child(_node_index(p), p)

    def default_value(self, argv):
        ex_msg = "Execute cmd(default_value %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node and its default value" % ex_msg)

        self.find_param(v[0]).set_item("default", v[1])

    def change_required(self, argv):
        ex_msg = "Execute cmd(change_required %s) failed, " % argv

        v = argv.split(" ")
        if len(v) != 2:
            raise Exception("%smust input node and its value" % ex_msg)

        self.find_param(v[0]).set_item("required",
                                       v[1].lower() in ["true", "yes", 1])

    def delete(self, node):
        p = self.find_param(node)
        p.parent.delete_child(_node_index(p))

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
        p.parent.delete_child(_node_index(p))
        parent.add_child(_node_index(p), p)

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

        n = "root_node" if parent == self else _node_index(parent)

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
            self._raise_if_duplicate_name(parent, v[0])
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
        p = mm_param.build([p], None, lambda n: n["name"], parent)[name]
        p.path[create_api_id] = name

        parent.add_child(_node_index(p), p)


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


def set_descs(tree, descs):
    for k, v in descs.items():
        tree.set_desc(k + " " + v)


def add_node(tree, node_info, api_info):
    if node_info["datatype"] in ("str", "int", "bool"):
        node_info.setdefault("mandatory", None)

        r = mm_param.build([node_info], None, lambda n: n["name"])
        node = r[node_info["name"]]

        for p in node_info["path"]:
            i = p.find(".")
            op_id = underscore(p[:i])
            index = p[i+1:]

            api = None
            for _, v in api_info.items():
                if v["op_id"] == op_id:
                    api = v
                    break
            else:
                raise Exception("add node failed, the unknown operation "
                                "id:%s" % p[:i])

            if api.get("msg_prefix"):
                index = index.replace(api.get("msg_prefix") + ".", "")

            try:
                find_parameter(index, api["body"], api["all_models"])
            except Exception as ex:
                raise Exception("add node failed, can't find parameter(%s) "
                                "referenced by property(%s), err:%s" % (
                                    index, node_info["name"], str(ex)))

            node.path[op_id] = index

        tree.add_child(_node_index(node), node)

    else:
        raise Exception("unsupported datatype(%s) for "
                        "add_node" % node_info["datatype"])


def adjust(adjust_cmds, properties, create_api_id, api_info):
    if not adjust_cmds:
        return

    rn = _Tree(properties)
    fm = {
        'rename': rn.rename,
        'delete': rn.delete,
        'merge_to': rn.merge_to,
        'move': rn.move,
        'set_desc': rn.set_desc,
        'add_path_param': functools.partial(rn.add_path_param, create_api_id),
        'default_value': rn.default_value,
        'change_required': rn.change_required,
    }

    for cmd in adjust_cmds:
        if isinstance(cmd, dict):
            if "set_desc" in cmd:
                set_descs(rn, cmd["set_desc"])

            elif "add_node" in cmd:
                add_node(rn, cmd["add_node"], api_info)

            else:
                raise Exception("unknown adjust cmd(%s)" % str(cmd))

            continue

        cmd = re.sub(r" +", " ", cmd)
        i = cmd.find(" ")
        f = fm.get(cmd[:i])
        if not f:
            raise Exception("Execute cmd(%s) failed, "
                            "unknown cmd(%s)" % (cmd, cmd[:i]))

        f(cmd[(i + 1):])

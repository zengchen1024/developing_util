import re


def _find_struct(datatype, all_models):
    if "datatype" in [
            'int', 'long', 'float', 'str', 'bool', 'date', 'datetime']:
        raise Exception("Can't find struct of datatype(%s)" % datatype)

    if datatype in all_models:
        return all_models[datatype]

    if datatype.startswith('list['):
        sub_datatype = re.match(r"list\[(.*)\]", datatype).group(1)
        return _find_struct(sub_datatype, all_models)

    if datatype.startswith('dict('):
        sub_datatype = re.match(r"dict\(([^,]*), (.*)\)", datatype).group(2)
        return _find_struct(sub_datatype, all_models)

    raise Exception("Can't find struct of datatype(%s) "
                    "in all models" % datatype)


def _find_parameter(name, struct, all_models):
    ns = name
    if isinstance(name, str):
        ns = name.split(".")

    if not ns:
        raise Exception("Can't find the parameter with no name")

    n = ns[0]

    if not isinstance(struct, list):
        raise Exception("Can't find the parameter(%s) in a Non-Struct "
                        "model" % n)

    p = None
    index = 0
    for i, v in enumerate(struct):
        if v["name"] == n:
            p = v
            index = i
            break
    else:
        raise Exception("Can't find the parameter(%s) in struct" % n)

    if len(ns) == 1:
        return index, struct

    return _find_parameter(
        ns[1:],
        _find_struct(p["datatype"], all_models),
        all_models)


def _change_type(index, parent, new_type):
    parent[index]["datatype"] = new_type


def preprocess(struct, all_models, cmds):
    m = {
        # "alone_parameter": lambda i, p: p[i]["alone_parameter"] = True,
        "delete": lambda i, p: p.pop(i),
        "change_type": _change_type,
    }

    for i in cmds:
        cmd = i.split(" ")

        f = m.get(cmd[0])
        if not f:
            raise Exception("Unknown pre-process cmd(%s)" % cmd[0])

        index, parent = _find_parameter(cmd[1], struct, all_models)
        f(index, parent, *cmd[2:])

import os
import re
import yaml


def build_path(path):
    for i in [r"{project_id}[/]*", r"{project}[/]*"]:
        m = re.search(i, path)
        if m:
            return path[m.end():]

    return path


def read_yaml(f):
    if not os.path.exists(f):
        return {}

    with open(f, 'r') as stream:
        try:
            return yaml.load(stream)
        except Exception as ex:
            raise Exception("Read %s failed, err=%s" % (f, ex))


def write_file(output, strs):
    with open(output, "w") as o:
        try:
            o.writelines(strs)
        except Exception:
            try:
                o.writelines(map(lambda s: s.encode("utf-8"), strs))
            except Exception as ex:
                raise Exception("Write file(%s) failed, %s" % (output, ex))


def normal_dir(path):
    return path + "/" if path[-1] != "/" else path


def remove_none(dict_v):
    for k in dict_v.keys():
        if not dict_v[k]:
            dict_v.pop(k)


def find_property(properties, path):
    items = path.split(".")
    obj = properties.get(items[0].strip())
    if not obj:
        raise Exception("parent:root, no child with key(%s)" % items[0])

    for k in items[1:]:
        obj = obj.child(k.strip())

    return obj


def underscore(v):
    v = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", v)
    v = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", v)
    return v.replace('-', '_').replace('.', '_').lower()


def process_override_codes(v, indent):
    r = []
    for row in v.split("\n"):
        row = row.strip("\t")
        r.append("%s%s" % (' ' * indent, row) if len(row) > 0 else row)
    return "\n".join(r)


def fetch_api(api_info, name):
    for  _, v in api_info.items():
        if v["name"] == name:
            return v

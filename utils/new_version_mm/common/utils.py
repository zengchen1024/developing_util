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

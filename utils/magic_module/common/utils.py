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
        return None

    with open(f, 'r') as stream:
        try:
            return yaml.load(stream)
        except Exception as ex:
            raise Exception("Read %s failed, err=%s" % (f, ex))

from os import listdir
from os.path import isfile, join
import re
import sys

def get_funtion_name(file_path):
    e = "^func(?: | \(.*\) )([a-zA-Z0-9_]+)\("
    return handle(file_path, e)


def get_invoked_funtion_name(file_path):
    e = "[ .]([a-zA-Z0-9_]+)\("
    return handle(file_path, e)


def handle(file_path, rege):
    r = set()
    with open(file_path, 'r') as o:
        for s in o.readlines():
            n = re.findall(rege, s)
            if n:
                r.update(n)
    return r


def all_function_name(directory):
    files = [f for f in listdir(directory) if isfile(join(directory, f))]
    return {f: get_funtion_name(join(directory, f)) for f in files}


def retrive_invoked_func(target):
    target_dir = target[0:target.rfind('/')]
    func_names = all_function_name(target_dir)

    def _retrive_single_file(file_name, indent):
        invoked_names = get_invoked_funtion_name(join(target_dir, file_name))
        for f, v in func_names.items():
            if f == file_name:
                continue
            i = invoked_names.intersection(v)
            if i:
                print("%s%s:  %s" % (' ' * indent, f, ", ".join(i)))
                _retrive_single_file(f, indent + 4)

    file_name = target[target.rfind('/') + 1:]
    print("\n    %s" % file_name)
    _retrive_single_file(file_name, 8)


if __name__ == "__main__":
    retrive_invoked_func(sys.argv[1])

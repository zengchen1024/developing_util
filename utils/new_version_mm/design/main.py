import os
import pystache
import sys
sys.path.append("..")

from resource_params_tree import generate_resource_properties
from common.utils import normal_dir, read_yaml


def run(api_path, cloud_name, tags, output):
    if not os.path.isdir(output):
        os.makedirs(output)
    output = normal_dir(output)

    if api_path[-1] != "/":
        api_path += "/"

    product = read_yaml(api_path + "product.yaml")
    if not product:
        raise Exception("Read (%s) failed" % (api_path + "product.yaml"))

    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")

    all_tags = {i["name"]: i for i in product["tags"]}
    for tag in tags.split(","):
        tag = tag.strip().decode("utf8")
        if tag not in all_tags:
            raise Exception("Unknown tag(%s)" % tag)

        _, properties = generate_resource_properties(
            api_yaml, all_models, tag,
            read_yaml(api_path + tag + ".yaml")
        )

        write_file(output + tag + ".yaml", _generate_yaml(properties))


def _generate_yaml(params, n=0):
    r = []
    keys = sorted(params.keys())
    for k in keys:
        v = params[k]
        s = v.to_param_yaml(n)
        if s:
            r.extend(s)
    return r


def write_file(output, strs):
    with open(output, "w") as o:
        try:
            o.writelines(strs)
        except Exception:
            try:
                o.writelines(map(lambda s: s.encode("utf-8"), strs))
            except Exception as ex:
                raise Exception("Write schema result failed, %s" % ex)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Input docx dir, cloud name, "
              "api tags(use , as delimiter), and output file")
        sys.exit(1)

    try:
        run(*sys.argv[1:])

    except Exception as ex:
        print(ex)
        sys.exit(1)

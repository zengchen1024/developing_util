import pystache
import sys

from resource import build_resource_config
from utils import read_yaml


def run(api_path, cloud_name, tags, output):
    cloud = None
    m = read_yaml("clouds.yaml")
    for i in m["clouds"]:
        if cloud_name == i["cloud_half_full_name"]:
            cloud = i
            break
    else:
        raise Exception("Unknown cloud(%s)" % cloud_name)

    if api_path[-1] != "/":
        api_path += "/"

    product = read_yaml(api_path + "product.yaml")
    if not product:
        raise Exception("Read (%s) failed" % (api_path + "product.yaml"))

    cloud["service_type"] = product["service_type"]
    r = []
    r.append(pystache.Renderer().render_path(
        "template/product.mustache", cloud))

    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")

    all_tags = {i["name"]: i for i in product["tags"]}
    for tag in tags.split(","):
        tag = tag.strip().decode("utf8")
        if tag not in all_tags:
            raise Exception("Unknown tag(%s)" % tag)

        r.extend(
            build_resource_config(
                api_yaml, all_models, all_tags[tag],
                read_yaml(api_path + tag + ".yaml"))
        )

    write_file(output, r)


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

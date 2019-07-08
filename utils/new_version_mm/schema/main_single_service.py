import os
import pystache
import re
import sys
sys.path.append("..")

from ansible import build_ansible_yaml
from api import build_resource_api_config
from common.utils import (normal_dir, read_yaml, write_file)
from design.resource_params_tree import generate_resource_properties
from resource import build_resource_config
from terraform import build_terraform_yaml


def run(config_file, cloud_name, tag, output):
    if not os.path.isdir(output):
        os.makedirs(output)

    output = normal_dir(output)
    api_path = os.path.dirname(config_file) + "/"

    cloud = _get_cloud_info(cloud_name)

    product = read_yaml(api_path + "product.yaml")
    if not product:
        raise Exception("Read (%s) failed" % (api_path + "product.yaml"))

    product_info = {"service_type": product["service_type"]}
    product_info.update(cloud)

    all_tags = {i["name"]: i for i in product["tags"]}
    tag = tag.strip().decode("utf8")
    if tag not in all_tags:
        raise Exception("Unknown tag(%s)" % tag)

    _generate_yaml(api_path, config_file, product_info, all_tags[tag], output)


def _generate_yaml(api_path, config_file, product_info, tag_info, output):
    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")
    custom_configs = read_yaml(config_file)
    api_info, properties = generate_resource_properties(
        api_yaml, all_models, custom_configs)
    argv = {
        "config_dir": api_path,
        "api_info": api_info,
        "properties": properties,
        "service_type": product_info["service_type"],
        "resource_name": _get_resource_name(tag_info, custom_configs),
        "version": _get_version(api_info),
        "resource_desc": tag_info.get("description", ""),
        "custom_configs": custom_configs,
        "cloud_full_name": product_info["cloud_full_name"],
        "cloud_short_name": product_info["cloud_short_name"],
    }

    r = [_render_product(product_info)]
    r.extend(build_resource_config(**argv))
    r.extend(build_resource_api_config(**argv))
    write_file(output + "api.yaml", r)

    _generate_platform_yaml(argv, output)


def _generate_platform_yaml(info, output):
    r = {
        "ansible": {
            "f": build_ansible_yaml,
            "data": [info]
        },
        "terraform": {
            "f": build_terraform_yaml,
            "data": [info]
        }
    }

    for k, v in r.items():
        if v["data"]:
            v["f"](v["data"], output)


def _get_cloud_info(cloud_name):
    cloud = None
    m = read_yaml("clouds.yaml")
    for i in m["clouds"]:
        if cloud_name == i["cloud_half_full_name"]:
            cloud = i
            break
    else:
        raise Exception("Unknown cloud(%s)" % cloud_name)

    return cloud


def _render_product(product_info):
    return pystache.Renderer().render_path(
        "template/product.mustache", product_info)


def _get_resource_name(tag_info, custom_configs):
    rn = tag_info["name"]
    if custom_configs:
        rn = custom_configs.get("resource_name", rn)

    if isinstance(rn, unicode):
        raise Exception("Must config resource_name in English, "
                        "because the tag is Chinese")

    s = rn[0].upper() + rn[1:]
    m = re.match(r"([A-Z]+[a-z0-9]*)+", s)
    if not m or m.end() != len(s):
        raise Exception("resouce name must comply with camel-case")

    return s


def _get_version(api_info):
    version = api_info["create"]["api"].get("version")
    if version:
        v = [i.strip().lower() for i in version.split(",")]
        v.sort()
        return v[-1].split(".")[0]
    return None


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

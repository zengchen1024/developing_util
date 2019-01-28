import os
import pystache
import sys
sys.path.append("..")

from ansible import build_ansible_yaml
from api import build_resource_api_config
from common.utils import normal_dir, read_yaml, write_file
from design.resource_params_tree import generate_resource_properties
from resource import build_resource_config
from terraform import build_terraform_yaml


def run(api_path, cloud_name, tags, output):
    if not os.path.isdir(output):
        os.makedirs(output)

    output = normal_dir(output)
    api_path = normal_dir(api_path)

    cloud = _get_cloud_info(cloud_name)

    product = read_yaml(api_path + "product.yaml")
    if not product:
        raise Exception("Read (%s) failed" % (api_path + "product.yaml"))

    product_info = {"service_type": product["service_type"]}
    product_info.update(cloud)

    all_tags = {i["name"]: i for i in product["tags"]}

    tag_info = {}
    for tag in tags.split(","):
        tag = tag.strip().decode("utf8")

        if tag not in all_tags:
            raise Exception("Unknown tag(%s)" % tag)

        tag_info[tag] = all_tags[tag]

    _generate_yaml(api_path, product_info, tag_info, output)


def _generate_yaml(api_path, product_info, tag_info, output):
    r = [_render_product(product_info)]
    override = {
        "ansible": {
            "f": build_ansible_yaml,
            "data": {}
        },
        "terraform": {
            "f": build_terraform_yaml,
            "data": {}
        }}

    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")

    for tag, v in tag_info.items():

        custom_configs = read_yaml(api_path + tag + ".yaml")

        api_info, properties = generate_resource_properties(
            api_yaml, all_models, tag, custom_configs
        )

        resource_name = _get_resource_name(v, custom_configs)
        service_type = product_info["service_type"]

        r.extend(
            build_resource_config(
                api_info, properties, resource_name,
                v.get("description", ""), service_type)
        )

        r.extend(
            build_resource_api_config(api_info, all_models,
                                      properties, custom_configs)
        )

        d = _generate_ansible_config(custom_configs)
        if d:
            override["ansible"]["data"][resource_name] = d

        d = _generate_terraform_config(api_path, product_info, api_info,
                                       custom_configs, resource_name)
        if d:
            override["terraform"]["data"][resource_name] = d

    write_file(output + "api.yaml", r)

    for item in override.values():
        if item["data"]:
            item["f"](item["data"], output)


def _generate_ansible_config(custom_configs):
    v = custom_configs.get("ansible")
    if v:
        return {
            "config": v,
        }


def _generate_terraform_config(api_path, product_info, api_info,
                               custom_configs, resource_name):

    v = custom_configs.get("terraform")
    if v:
        prefix = "%s_%s" % (product_info["cloud_full_name"],
                            product_info["service_type"])

        return {
            "config": v,
            "config_dir": api_path,
            "api_info": api_info,
            "resource_name": "%s_%s" % (prefix, resource_name.lower())
        }


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

    return rn[0].upper() + rn[1:]


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

import os
import pystache
import sys
sys.path.append("..")


from ansible import build_ansible_yaml
from api import build_resource_api_config
from common.utils import normal_dir, read_yaml, write_file
from design.resource_params_tree import generate_resource_properties
from resource import build_resource_config
from resource import get_resource_name
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

    _generate_api_yaml(api_path, product_info, tag_info, output)

    _generate_platform_yaml(api_path, product_info, tag_info, output)


def _generate_api_yaml(api_path, product_info, tag_info, output):
    r = [_render_product(product_info)]

    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")

    for tag, v in tag_info.items():

        custom_configs = read_yaml(api_path + tag + ".yaml")

        api_info, properties = generate_resource_properties(
            api_yaml, all_models, tag, custom_configs
        )

        r.extend(
            build_resource_config(
                api_info, properties, v,
                custom_configs, product_info["service_type"])
        )

        r.extend(
            build_resource_api_config(api_info, all_models,
                                      properties, custom_configs)
        )

    write_file(output + "api.yaml", r)


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
    return pystache.Renderer().render_path("template/product.mustache",
                                           product_info)


def _generate_platform_yaml(api_path, product_info, tag_info, output):
    prefix = "%s_%s" % (product_info["cloud_full_name"],
                        product_info["service_type"])

    config = {"ansible": {}, "terraform": {}}

    for tag, info in tag_info.items():
        custom_configs = read_yaml(api_path + tag + ".yaml")

        rn = get_resource_name(info, custom_configs)

        v = custom_configs.get("ansible")
        if v:
            config["ansible"][rn] = {
                "config": v,
            }

        v = custom_configs.get("terraform")
        if v:
            config["terraform"][rn] = {
                "config": v,
                "config_dir": api_path,
                "terraform_resource_name": "%s_%s" % (prefix, rn.lower())
            }

    m = {
        "ansible": build_ansible_yaml,
        "terraform": build_terraform_yaml
    }
    for k, v in config.items():
        m[k](v, output)


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

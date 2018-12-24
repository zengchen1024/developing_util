import os
import pystache
import sys
sys.path.append("..")


from ansible import build_ansible_yaml
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

    product = read_yaml(api_path + "product.yaml")
    if not product:
        raise Exception("Read (%s) failed" % (api_path + "product.yaml"))

    all_tags = {i["name"]: i for i in product["tags"]}

    tag_info = {}
    for tag in tags.split(","):
        tag = tag.strip().decode("utf8")

        if tag not in all_tags:
            raise Exception("Unknown tag(%s)" % tag)

        tag_info[tag] = all_tags[tag]

    _generate_api_yaml(api_path, cloud_name, tag_info,
                       product["service_type"], output)

    _generate_platform_yaml(api_path, tag_info, output)


def _generate_api_yaml(api_path, cloud_name, tag_info, service_type, output):
    r = [
        _render_product(cloud_name, service_type)
    ]

    api_yaml = read_yaml(api_path + "api.yaml")
    all_models = read_yaml(api_path + "models.yaml")

    for tag, v in tag_info.items():

        custom_configs = read_yaml(api_path + tag + "_design.yaml")

        api_info, properties = generate_resource_properties(
            api_yaml, all_models, tag, custom_configs
        )

        r.extend(
            build_resource_config(
                api_info, properties, v,
                custom_configs, service_type)
        )

    write_file(output + "api.yaml", r)


def _render_product(cloud_name, service_type):
    cloud = None
    m = read_yaml("clouds.yaml")
    for i in m["clouds"]:
        if cloud_name == i["cloud_half_full_name"]:
            cloud = i
            break
    else:
        raise Exception("Unknown cloud(%s)" % cloud_name)

    cloud["service_type"] = service_type

    return pystache.Renderer().render_path("template/product.mustache", cloud)


def _generate_platform_yaml(api_path, tag_info, output):
    config = {"ansible": {}, "terraform": {}}

    for tag, info in tag_info.items():
        custom_configs = read_yaml(api_path + tag + "_design.yaml")

        rn = get_resource_name(info, custom_configs)

        v = custom_configs.get("ansible")
        if v:
            config["ansible"][rn] = v

        v = custom_configs.get("terraform")
        if v:
            config["terraform"][rn] = v

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

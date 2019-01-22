import pystache
import re

from common.utils import remove_none


class _Resource(object):
    def __init__(self, name, service_type, desc, parameter, properties):
        self._name = name
        self._service_type = service_type
        self._description = desc
        self._parameters = parameter
        self._properties = properties

    def render(self):
        v = {
            "name": self._name,
            "service_type": self._service_type,
            "description": self._description,
        }
        remove_none(v)

        r = [
            pystache.Renderer().render_path("template/resource.mustache", v)
        ]
        r.extend(self._generate_parameter_config())
        return r

    def _generate_parameter_config(self):

        def _generate_yaml(params, n):
            r = []
            keys = sorted(params.keys())
            for k in keys:
                v = params[k]
                s = v.to_yaml(n)
                if s:
                    r.extend(s)
            return r

        r = []
        indent = 4
        if self._parameters:
            r.append("%sparameters:\n" % (' ' * indent))
            r.extend(_generate_yaml(self._parameters, indent + 2))

        r.append("%sproperties:\n" % (' ' * indent))
        r.extend(_generate_yaml(self._properties, indent + 2))
        return r


def get_resource_name(tag_info, custom_configs):
    rn = tag_info["name"]
    if custom_configs:
        rn = custom_configs.get("resource_name", rn)

    if isinstance(rn, unicode):
        raise Exception("Must config resource_name in English, "
                        "because the tag is Chinese")

    return rn[0].upper() + rn[1:]


def build_resource_config(api_info, properties, tag_info,
                          custom_configs, service_type):
    params = {}
    pros = {}
    for k, v in properties.items():
        if "r" in v.get_item("crud"):
            pros[k] = v
        else:
            params[k] = v

    resource = _Resource(
        get_resource_name(tag_info, custom_configs),
        service_type, tag_info.get("description", ""),
        params, pros)

    return resource.render()
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
    rn = get_resource_name(tag_info, custom_configs)

    identity = custom_configs.get("identity")
    if not identity:
        raise Exception("Must config identity to verify the rsource")

    params = {}
    pros = {}
    for k, v in properties.items():
        if "r" in v.get_item("crud"):
            pros[k] = v

        else:
            params[k] = v

    v = set(identity) - set([v.get_item("name") for v in pros.values()])
    if v:
        raise Exception("Not all items(%s) of identity are in "
                        "resource's properties" % ", ".joint(v))

    rid = custom_configs.get("resource_id")
    if rid:
        if rid not in pros:
            raise Exception("Can't find the property(%s) in properties" % rid)

        pros[rid].set_item("is_id", True)

    resource = _Resource(rn, service_type, tag_info.get("description", ""),
                         params, pros)

    return resource.render()

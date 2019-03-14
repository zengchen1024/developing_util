import pystache
import re

from common.utils import write_file, find_property


def build_terraform_yaml(info, output):
    data = []
    for v in info:
        r = {}
        config = v.get("custom_configs")["terraform"]

        examples = config.get("examples")
        if examples:
            r.update(_generate_example_config(examples, v))

        overrides = config.get("properties")
        if overrides:
            _generate_property_override(
                overrides, v["api_info"], v["properties"],
                v["resource_name"], r)

        overrides = config.get("api_asyncs")
        if overrides:
            _generate_async_override(overrides, v["api_info"], r)

        if r:
            r["name"] = v["resource_name"]
            data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])


def _generate_property_override(overrides, api_info, properties,
                                resource_name, result):
    req_apis = {}
    for v in api_info.values():
        if v["crud"].find("r") == -1:
            req_apis[v["op_id"]] = v.get("type", v["op_id"])

    override_properties = set(["to_request", "from_response"])

    pros = []
    params = []
    for path, v in overrides.items():
        e = set(v.keys()) - override_properties
        if e:
            raise Exception("find unspported override properties(%s) "
                            "for resource(%s)" % (" ".join(e), resource_name))

        prop = find_property(properties, path)

        v1 = v.get("to_request")
        if v1:
            for k, p in prop.path.items():
                if k in req_apis:
                    params.append({
                        "prop_path": req_apis.get(k) + "." + p,
                        "var_name": "to_request",
                        "var_value": _process_lines(v1, 10)
                    })

        v1 = v.get("from_response")
        if v1:
                pros.append({
                    "prop_path": path,
                    "var_name": "from_response",
                    "var_value": _process_lines(v1, 10)
                })

    if pros:
        result["properties"] = pros
        result["has_property_override"] = True

    if params:
        result["parameters"] = params
        result["has_parameter_override"] = True


def _process_lines(v, indent):
    return "\n".join([
        "%s%s" % (' ' * indent, row.strip().strip("\t"))
        for row in v.split("\n")
    ])


def _generate_async_override(api_asyncs, api_info, result):
    def _api_key(p):
        for v in api_info.values():
            if v["op_id"] == p:
                return v.get("type", p)

    if api_asyncs:
        pros = []
        for p, v1 in api_asyncs.items():
            v2 = {"api": _api_key(p)}
            v2.update(v1)

            pros.append(v2)

        result["api_asyncs"] = pros
        result["has_async_override"] = True


def _generate_example_config(examples, info):
    trn = ("%s_%s_%s_%s" % (
        info["cloud_full_name"], info["service_type"],
        info["resource_name"], info["version"])).lower()

    m = re.compile(r"resource \"%s\" \"(.*)\" {" % trn)

    def _find_id(f):
        tf = None
        with open(f, "r") as o:
            tf = o.readlines()

        r = []
        for i in tf:
            v = m.match(i)
            if v:
                r.append(v)

        if len(r) != 1:
            raise Exception("Find zero or one more terraform resource(%s) "
                            "in tf file(%s)" % (trn, f))

        return r[0].group(1)

    result = [
        {
            "name": f.split(".")[0],
            "resource_id": _find_id(info["config_dir"] + f)
        }
        for f in examples
    ]
    if result:
        result[0]["is_basic"] = True

    return {"examples": result, "has_example": len(result) > 0}

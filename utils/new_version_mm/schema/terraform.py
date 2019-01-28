import pystache
import re

from common.utils import write_file


def build_terraform_yaml(info, output):
    data = []
    for rn, v in info.items():
        r = {}
        config = v.get("config")

        examples = config.get("examples")
        if examples:
            r.update(_generate_example_config(examples, v))

        overrides = config.get("overrides")
        if overrides:
            _generate_property_override(overrides, rn, r)

        overrides = config.get("api_asyncs")
        if overrides:
            _generate_async_override(overrides, v["api_info"], r)

        if r:
            r["name"] = rn
            data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])


def _generate_property_override(overrides, resource_name, result):
    override_properties = set(["to_create", "to_update", "from_response"])

    pros = []
    for p, v1 in overrides.items():
        e = set(v1.keys()) - override_properties
        if e:
            raise Exception("find unspported override properties(%s) "
                            "for resource(%s)" % (" ".join(e), resource_name))

        v2 = {"property": p}
        v2.update(v1)

        pros.append(v2)

    result["properties"] = pros
    result["has_property_override"] = True


def _generate_async_override(api_asyncs, api_info, result):
    def _api_key(p):
        for v in api_info.values():
            if v["op_id"] == p:
                return v.get("type") if v.get("type") else p

    if api_asyncs:
        pros = []
        for p, v1 in api_asyncs.items():
            v2 = {"api": _api_key(p)}
            v2.update(v1)

            pros.append(v2)

        result["api_asyncs"] = pros
        result["has_async_override"] = True


def _generate_example_config(examples, info):
    trn = info["resource_name"]
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

import pystache
import re

from common.utils import write_file


def build_terraform_yaml(info, output):
    override_properties = set(["to_create", "to_update", "from_response"])
    data = []
    for rn, v in info.items():
        r = {}
        config = v.get("config")

        example = config.get("example")
        if example:
            e = _generate_example_config(example, v)
            if e:
                r.update(e)

        overrides = config.get("overrides")
        if overrides:
            pros = []
            for p, v1 in overrides.items():
                e = set(v1.keys()) - override_properties
                if e:
                    raise Exception("find unspported override properties(%s) "
                                    "for resource(%s)" % (" ".join(e), rn))

                v2 = {"property": p}
                v2.update(v1)

                pros.append(v2)

            r["properties"] = pros
            r["has_property_override"] = True

        if r:
            r["name"] = rn
            data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])


def _generate_example_config(example, info):
    f = example.get("tf_file")
    if not f:
        return None

    trn = info["terraform_resource_name"]
    m = re.compile(r"resource \"%s\" \"(.*)\" {" % trn)

    path = info["config_dir"]
    tf = None
    with open(path + f, "r") as o:
        tf = o.readlines()

    r = []
    for i in tf:
        v = m.match(i)
        if v:
            r.append(v)

    if len(r) != 1:
        raise Exception("Find zero or one more terraform resource(%s) in tf "
                        "file(%s)" % (trn, path + f))

    return {"example": {"name": f.split(".")[0], "resource_id": r[0].group(1)}}

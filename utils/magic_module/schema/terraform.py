import pystache
from common.utils import write_file


def build_terraform_yaml(config, output):
    override_properties = set(["to_create", "to_update", "from_response"])
    data = []
    for rn, v in config.items():
        r = {"name": rn}

        examples = v.get("examples")
        if not examples:
            raise Exception("must config example for resource(%s)" % rn)

        overrides = v.get("overrides")
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

        data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])

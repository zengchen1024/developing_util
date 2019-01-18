import pystache
from common.utils import write_file


def build_ansible_yaml(ansible, output):
    override_properties = set(["to_create", "to_update", "from_response"])
    data = []
    for rn, v in ansible.items():
        overrides = v.get("overrides")
        if not overrides:
            continue

        pros = []
        for p, v1 in overrides.items():
            e = set(v1.keys()) - override_properties
            if e:
                raise Exception("find unspported override properties(%s) "
                                "for resource(%s)" % (" ".join(e), rn))

            v2 = {"property": p}
            v2.update(v1)

            pros.append(v2)

        data.append({"name": rn, "properties": pros})

    s = pystache.Renderer().render_path("template/ansible.mustache",
                                        {"resources": data})

    write_file(output + "ansible.yaml", [s])

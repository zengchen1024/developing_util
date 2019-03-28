from collections import namedtuple
import docx
import pystache
import re
import sys
sys.path.append("..")

from common.utils import write_file


PropertyDef = namedtuple(
    "PropertyDef", ["name", "mandatory", "datatype", "desc"])


class Struct(object):
    def __init__(self, name):
        self._name = name
        self._properties = []
        self._required = []

    def add_property(self, properties):
        for p in properties:
            if p.mandatory == "yes":
                self._required.append(p.name)

            d = {
                "name": p.name,
                "description": _desc_yaml(8, "description", p.desc)
            }
            d.update(_parse_datatype(p.datatype))

            self._properties.append(d)

        return self

    def to_map(self):
        d = {
            "name": self._name,
        }

        if self._required:
            d["has_required"] = True
            d["required"] = [{"item": i} for i in self._required]

        d["properties"] = self._properties

        return d


def _parse_word(file_name):

    tables = {}
    doc = docx.Document(file_name)

    for table in doc.tables:
        t = []
        tn = ""
        column_desc = None

        for i, row in enumerate(table.rows):
            # remove the overstriking tag(\xa0)
            cells = [c.text.replace(u"\xa0", u" ") for c in row.cells]

            if i == 0:
                # table name
                tn = cells[0]
                continue
            elif i == 1 and cells[0] == "Parameter":
                # column description
                column_desc = {v.lower(): j for j, v in enumerate(cells)}
                continue

            items = cells
            if column_desc:
                items = [
                    cells[column_desc[p]] if p in column_desc else None
                    for p in [
                        "parameter", "mandatory", "type", "description"
                    ]
                ]

            try:
                r = PropertyDef(
                    items[0],
                    items[1].lower() if items[1] else 'no',
                    items[2],
                    items[3].strip("\n"),
                )
                t.append(r)
            except Exception as ex:
                raise Exception(
                    "Convert file:%s, table:%s, parameter:%s, failed, err=%s" %
                    (file_name, tn, items[0], ex)
                )

        tables[tn] = t

    return tables


def _parse_datatype(datatype):
    type_map = {
        "string":       'string',
        "uuid":         'string',
        "integer":      'integer',
        "number":       'integer',
        "int":          'integer',
        "boolean":      'boolean',
    }

    dt = datatype.strip().lower()
    if dt in type_map:
        return {"type": type_map[dt]}

    if dt in ("timestamp", "time"):
        return {
            "type": "string",
            "format": "date-time"
        }

    ts = ("list<string>", "list[string]", "string array",
          "[string]", "stringarray")
    if dt in ts:
        return {
            "type": "array",
            "items": {
                "type": "string"
            }
        }

    m = re.match(
        r"^list\[object:|^\[object:|^list<object:|^jsonarray:|^array:", dt)
    if m:
        t = datatype[m.end():]
        if t[-1] in (']', '>'):
            t = t[:-1]

        item = None
        if t in type_map:
            item = {"type": type_map[t]}
        else:
            item = {"$ref": "#/definitions/%s" % t}

        return {
            "type": "array",
            "items": item
        }

    m = re.match(r"^object:|^jsonobject:|^dict:", dt)
    if m:
        return {
            "$ref": "#/definitions/%s" % datatype[m.end():]
        }

    m = re.match(r"^map:", dt)
    if m:
        t = datatype[m.end():]
        ap = None
        if t in type_map:
            ap = {"type": type_map[t]}
        else:
            ap = {"$ref": "#/definitions/%s" % t}

        return {
            "type": "object",
            "additionalProperties": ap
        }

    raise Exception("Unknown parameter type: %s" % datatype)


def _desc_yaml(indent, k, v):

    def _paragraph_yaml(p, indent, max_len):
        r = []
        s1 = p
        while len(s1) > max_len:
            # +1, because maybe the s1[max_len] == ' '
            i = s1.rfind(" ", 0, max_len + 1)
            s2, s1 = (s1[:max_len], s1[max_len:]) if i == -1 else (
                s1[:i], s1[(i + 1):])
            r.append("%s%s\n" % (' ' * indent, s2))
        if s1:
            r.append("%s%s\n" % (' ' * indent, s1))

        return "".join(r)

    result = []
    indent += 2
    max_len = 79 - indent
    if max_len < 20:
        max_len = 20

    for p in v.split("\n"):
        if not p:
            continue
        result.append(_paragraph_yaml(p, indent, max_len))

    result[-1] = result[-1][:-1]
    return "".join(result)


def run(file_name, output):
    tables = _parse_word(file_name)
    data = [Struct(k).add_property(v).to_map() for k, v in tables.items()]

    s = pystache.Renderer().render_path("struct.mustache", {"structs": data})

    write_file(output, [s])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Input docx file and output file")
        sys.exit(1)

    try:
        run(*sys.argv[1:])
    except Exception as ex:
        print(ex)
        sys.exit(1)

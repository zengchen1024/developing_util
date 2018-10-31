from collections import namedtuple
import docx
import re


ParamDef = namedtuple("ParamDef", ["name", "mandatory", "ptype", "desc"])


def word_to_params(file_name):

    mandatory = None
    for n in ["get.docx", "create_rsp.docx", "update_rsp.docx"]:
        if file_name.find(n) >=0:
            mandatory = "no"
            break

    tables = {}
    doc = docx.Document(file_name)

    for table in doc.tables:
        t = {}
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
                m = mandatory
                if m is None:
                    m = items[1].lower() if items[1] else 'no'

                r = ParamDef(
                    items[0],
                    m,
                    _parse_param_type(items[2]),
                    items[3].strip("\n"),
                )
                t[items[0]] = r
            except Exception as ex:
                raise Exception(
                    "Convert file:%s, table:%s, parameter:%s, failed, err=%s" %
                    (file_name, tn, items[0], ex)
                )

        #try:
        #    cls._check_param_name_of_table(t)
        #except Exception as ex:
        #    raise Exception("Convert file:%s, table:%s, failed, err=%s" %
        #                    (file_name, tn, ex))

        tables[tn] = t

    return tables


def _check_param_name_of_table(struct):
    """all the lowercase parameter names in a struct should be different"""

    names = [i.param.lower() for i in struct]
    s = set(names)
    if len(s) != len(names):
        m = {i:0 for i in s}
        for i in names:
            m[i] += 1
        ns = [k for k, v in m.items() if v > 1]
        raise Exception("Not All lowercase parameter names are different: %s" %
                        " ".join(ns))


def _parse_param_type(ptype):
    type_map = {
        "string":       'string',
        "uuid":         'string',
        "integer":      'int',
        "number":       'int',
        "boolean":      'bool',
        "list<string>": '[]string',
        "list[string]": '[]string',
        "string array": '[]string',
        "timestamp":    'string',
        "time":         'string',
        "enumerated":   'string',
        "enum":         'string',
        "map":          'interface{}',
    }

    l = ptype.strip().lower()
    if l in type_map:
        return type_map[l]

    m = re.match("^list\[object:", l)
    if m:
        return "[]%s" % ptype[m.end():][:-1]

    m = re.match("^\[object:", l)
    if m:
        return "[]%s" % ptype[m.end():][:-1]

    m = re.match("^object:", l)
    if m:
        return ptype[m.end():]

    raise Exception("Unknown parameter type: %s" % ptype)

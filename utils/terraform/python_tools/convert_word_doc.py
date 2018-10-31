from collections import namedtuple
import docx
import re


ParamDef = namedtuple("ParamDef", ["param", "mandatory", "param_type", "desc"])


class WordDocPretreatment(object):

    @classmethod
    def req_struct(cls, req_file):
        return cls._read_doc(req_file)

    @classmethod
    def resp_struct(cls, resp_file):
        return cls._read_doc(resp_file)

    @classmethod
    def _read_doc(cls, file_name, handle=None):

        def _handle(items):
            if handle:
                return handle(items)

            return ParamDef(
                items[0],
                items[1].lower(),
                cls._parse_param_type(items[2]),
                items[3].replace("\n", " "),
            )


        tables = {}
        doc = docx.Document(file_name)

        for table in doc.tables:
            t = []
            tn = ""
            column_desc = None

            for i, r in enumerate(table.rows):
                # remove the overstriking tag(\xa0)
                items = [c.text.replace(u"\xa0", u" ") for c in r.cells]

                if i == 0:
                    # table name
                    tn = items[0]
                elif i == 1 and items[0] == "Parameter":
                    # column description
                    column_desc = {v.lower(): ii for ii, v in enumerate(items)}
                else:
                    cis = items
                    if column_desc:
                        cis = [items[column_desc[p]] if p in column_desc else ""
                             for p in ["parameter", "mandatory", "type", "description"]
                        ]

                    try:
                        row = _handle(cis)
                        if row:
                            t.append(row)
                    except Exception as ex:
                        raise Exception("Convert docx file:%s, table:%s, parameter:%s, failed, "
                                        "err=%s" % (file_name, tn, cis[0], ex))

            try:
                cls._check_param_name_of_table(t)
            except Exception as ex:
                raise Exception("Convert docx file:%s, table:%s, failed, err=%s" % (file_name, tn, ex))

            tables[tn] = t

        return tables

    @classmethod
    def _check_param_name_of_table(cls, rows):
        """all the lowercase parameter names in a struct should be different"""

        names = [i.param.lower() for i in rows]
        s = set(names)
        if len(s) != len(names):
            m = {i:0 for i in s}
            for i in names:
                m[i] += 1
            ns = [k for k, v in m.items() if v > 1]
            raise Exception("Not All lowercase parameter names are different: %s" % " ".join(ns))

    @classmethod
    def _parse_param_type(cls, type_str):
        type_map = {
            "string":       'string',
            "integer":      'int',
            "boolean":      'bool',
            "list<string>": '[]string',
            "list[string]": '[]string',
        }

        l = type_str.lower()
        if l in type_map:
            return type_map[l]

        m = re.match("^list\[object:", l)
        if m:
            return "[]%s" % type_str[m.end():][:-1]

        m = re.match("^object:", l)
        if m:
            return type_str[m.end():]

        raise Exception("Unknown parameter type: %s" % type_str)

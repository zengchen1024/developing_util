import sys

from convert_word_doc import word_to_params


class Basic(object):

    def __init__(self, go_file, docx_file):
        self._go_file = go_file
        self._docx_file = docx_file

    def build_go_file(self):
        try:
            tables = word_to_params(self._docx_file)
        except Exception as ex:
            raise Exception("Parse %s failed, error=%s" % (self._docx_file, ex))

        result = self._generate_structs(tables)

        self._write_go_file(result)

    def _write_go_file(self, result):
        try:
            with open(self._go_file, 'a') as fo:
                fo.writelines(result)
        except Exception as ex:
            raise Exception("Parse %s success, but write go file:%s failed, "
                  "error:%s" % (self._docx_file, self._go_file, ex))

    def _generate_structs(self, tables):
        struct_names = {
            n: "".join([i[0].capitalize() + i[1:] for i in n.split("_")])
            for n in tables
        }
        def _get_para_type(t):
            if t.startswith('['):
                t = t[2:]
                return '[]' + struct_names.get(t)
            return struct_names.get(t, t)

        result = []

        #import pdb
        #pdb.set_trace()
        for table_name, table in tables.items():
            try:
                result.append("type %s struct {\n" % struct_names[table_name])
                for _, opt in table.items():
                    result.append(
                        self._convert_to_struct_member(opt, _get_para_type))
                result.append("}\n\n")

            except Exception as ex:
                raise Exception("Parse %s : table(%s) to generate struct failed, "
                      "err=%s" % (self._docx_file, table_name, ex))

        return result

    def _convert_to_struct_member(self, opt):
        return ""

    @classmethod
    def _to_struct_member_name(cls, param_name):
        return "".join(
            ["ID" if i == "id" else i.capitalize()
             for i in param_name.split("_")]
        )


class ReqOpts(Basic):

    def _convert_to_struct_member(self, opt, func):
        templ = {
            "yes": '\t%(name)s %(type)s `json:"%(para)s" required:"true"`\n',
            "no":  '\t%(name)s %(type)s `json:"%(para)s,omitempty"`\n',
        }

        if opt.mandatory not in templ:
            raise Exception("unknown mandatory for parameter:%s" % opt.param)

        return templ[opt.mandatory] % {
            'name': self._to_struct_member_name(opt.name),
            "type": func(opt.ptype),
            "para": opt.name,
        }


class RespOpts(Basic):

    def _convert_to_struct_member(self, opt, func):
        return '%(name)s %(type)s `json:"%(param)s"`\n' % {
            'name': self._to_struct_member_name(opt.name),
            "type": func(opt.ptype),
            "param": opt.name,
        }


if __name__ == "__main__":
    m = {
        "req": ReqOpts,
        "resp": RespOpts
    }

    try:
        m[sys.argv[1]](*sys.argv[2:]).build_go_file()
    except Exception as ex:
        print("Run convert_request_response.py failed: %s" % ex)
        sys.exit(1)
    sys.exit(0)

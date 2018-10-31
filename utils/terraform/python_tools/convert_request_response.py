import sys

import convert_word_doc


class Basic(object):

    def __init__(self, go_file, docx_file):
        self._go_file = go_file
        self._docx_file = docx_file
        self._methods = ""

    def build_go_file(self):
        tables = self._read_word_doc()
        if not tables:
            return

        descs = self._generate_structs(tables)

        if self._methods:
            descs.append(self._methods)

        self._write_go_file(descs)

    def _write_go_file(self, descs):
        go_file = self._go_file
        fo = None
        try:
            fo = open(go_file, "a")
            for desc in descs:
                fo.writelines(desc)
        except Exception as ex:
            raise "Edit go file:%s error:%s" % (go_file, ex)
        finally:
            if fo:
                fo.close()

    def _generate_structs(self, tables):
        structs = []

        for table_name, rows in tables.items():
            try:
                struct_desc = "type %s struct {\n" % table_name
                for opt in rows:
                    struct_desc += self._convert_to_struct_member(opt)
                struct_desc += "}\n\n"
                structs.append(struct_desc)
            except Exception as ex:
                raise "Convert table:%s to struct failed, err=%s" % (table_name, ex)

        return structs

    def _read_word_doc(self):
        return None

    def _convert_to_struct_member(self, opt):
        return ""

    @classmethod
    def _to_struct_member_name(cls, param_name):
        return "".join(
            ["ID" if i == "id" else i.capitalize()
             for i in param_name.split("_")]
        )


class ReqOpts(Basic):

    def _read_word_doc(self):
        return convert_word_doc.WordDocPretreatment.req_struct(self._docx_file)

    def _convert_to_struct_member(self, opt):
        templ = {
            "yes": '\t%(name)s %(type)s `json:"%(para)s" required:"true"`\n',
            "no":  '\t%(name)s %(type)s `json:"%(para)s,omitempty"`\n',
        }

        if opt.mandatory not in templ:
            raise Exception("unknown mandatory for parameter:%s" % opt.param)

        return templ[opt.mandatory] % {
            'name': self._to_struct_member_name(opt.param),
            "type": opt.param_type,
            "para": opt.param,
        }


class RespOpts(Basic):

    def _read_word_doc(self):
        return convert_word_doc.WordDocPretreatment.resp_struct(self._docx_file)

    def _convert_to_struct_member(self, node):
        return '%(name)s %(type)s `json:"%(param)s"`\n' % {
            'name': self._to_struct_member_name(node.param),
            "type": node.param_type,
            "param": node.param,
        }


class CreateOpts(ReqOpts):
    def __init__(self, go_file, docx_file, resource_name, req_success_codes):
        super(CreateOpts, self).__init__(go_file, docx_file)

        self._methods = self._generate_methods(resource_name, req_success_codes)

    def _generate_methods(self, resource_name, req_success_codes):
        req_opt = "nil"
        if req_success_codes:
            req_opt = "&golangsdk.RequestOpts{OkCodes: []int{%s}}" % req_success_codes

        return """type CreateOptsBuilder interface {
\tTo%(resource)sCreateMap() (map[string]interface{}, error)
}

func (opts CreateOpts) To%(resource)sCreateMap() (map[string]interface{}, error) {
\treturn golangsdk.BuildRequestBody(opts, "")
}

func Create(c *golangsdk.ServiceClient, opts CreateOptsBuilder) (r CreateResult) {
\tb, err := opts.To%(resource)sCreateMap()
\tif err != nil {
\t\tr.Err = err
\t\treturn
\t}
\tlog.Printf("[DEBUG] create url:%%q, body=%%#v", createURL(c), b)
\treqOpt := %(req_opt)s
\t_, r.Err = c.Post(createURL(c), b, &r.Body, reqOpt)
\treturn
}

""" % {"resource": resource_name, "req_opt": req_opt}


class UpdateOpts(ReqOpts):
    def __init__(self, go_file, docx_file, resource_name, req_success_codes, rest_method):
        super(UpdateOpts, self).__init__(go_file, docx_file)

        self._methods = self._generate_methods(resource_name, req_success_codes, rest_method)

    def _generate_methods(self, resource_name, req_success_codes, rest_method):
        req_opt = "nil"
        if req_success_codes:
            req_opt = "&golangsdk.RequestOpts{OkCodes: []int{%s}}" % req_success_codes

        return """type UpdateOptsBuilder interface {
\tTo%(resource)sUpdateMap() (map[string]interface{}, error)
}

func (opts UpdateOpts) To%(resource)sUpdateMap() (map[string]interface{}, error) {
\treturn golangsdk.BuildRequestBody(opts, "")
}

func Update(c *golangsdk.ServiceClient, id string, opts UpdateOptsBuilder) (r UpdateResult) {
\tb, err := opts.To%(resource)sUpdateMap()
\tif err != nil {
\t\tr.Err = err
\t\treturn
\t}
\tlog.Printf("[DEBUG] update url:%%q, body=%%#v", updateURL(c, id), b)
\treqOpt := %(req_opt)s
\t_, r.Err = c.%(method)s(updateURL(c, id), b, &r.Body, reqOpt)
\treturn
}

""" %   {
            "resource": resource_name,
            "req_opt": req_opt,
            "method": rest_method,
        }


if __name__ == "__main__":
    m = {
        "req_create": CreateOpts,
        "req_update": UpdateOpts,
        "resp": RespOpts
    }
    try:
        m[sys.argv[1]](*sys.argv[2:]).build_go_file()
    except Exception as ex:
        print "Run convert_request_response.py failed: %s", ex
        sys.exit(1)
    sys.exit(0)

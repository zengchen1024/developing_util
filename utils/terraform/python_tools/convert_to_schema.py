from collections import namedtuple
import os
import re
import sys
import convert_word_doc
import read_request_go_file


OptParamTypeKind = (
    TypeKindSimple,      # string, int, bool
    TypeKindSimpleList,  # []string, []int, []bool
    TypeKindStruct,      # struct
    TypeKindStructList,  # []struct
) = (
    "Simple",
    "SimpleList",
    "Struct",
    "StructList",
)


OptKind = (
    OptKindRequired,
    OptKindOptional,
    OptKindOptionalComputed,
    OptKindComputed,
) = (
    "Required",
    "Optional",
    "OptionalComputed",
    "Computed",
)


ParamTypeInfo = namedtuple("ParamTypeInfo", "type_kind, go_type, terraform_type")


OptDef = namedtuple("OptDef", "schema_name, opt_kind, param_type_info, desc")


ParamDef = namedtuple("ParamDef", "name, param_type, tag, desc")


class ConvertToSchema(object):

    def __init__(self, ):
        self._structs = {}
        self._struct_names = []

    def pre_run(self, resource_name, sdk_dir, api_doc_dir, req_struct_names, resp_struct_names):
        req_struct_names = req_struct_names.split("\n")
        resp_struct_names = resp_struct_names.split("\n")

        self._struct_names.extend(req_struct_names)
        self._struct_names.extend(resp_struct_names)

        req_structs = read_request_go_file.RequestStruct.get_struct_def("%s/requests.go" % sdk_dir, req_struct_names)
        self._check_update_create_opts(req_structs)

        create_docx = "%s/create.docx" % api_doc_dir
        if not os.path.exists(create_docx):
            raise Exception("%s is not exists" % create_docx)
        req_doc = convert_word_doc.WordDocPretreatment.req_struct(create_docx)

        update_docx = "%s/update.docx" % api_doc_dir
        if os.path.exists(update_docx):
            req_doc.update(convert_word_doc.WordDocPretreatment.req_struct(update_docx))

        req_structs = self._add_desc(req_structs, req_doc)

        get_docx = "%s/get.docx" % api_doc_dir
        if os.path.exists(get_docx):
            resp_doc = convert_word_doc.WordDocPretreatment.req_struct(get_docx)
            resp_structs = read_request_go_file.RequestStruct.get_struct_def("%s/results.go" % sdk_dir, resp_struct_names)
            resp_structs = self._add_desc(resp_structs, resp_doc)

            self._merge_structs(req_structs, "CreateOpts", resp_structs, resource_name)
        else:
            self._parse_req_struct(req_structs, "CreateOpts")

    def run(self, resource_name, resource_file, sdk_dir, api_doc_dir, req_struct_names, resp_struct_names):

        self.pre_run(resource_name, sdk_dir, api_doc_dir, req_struct_names, resp_struct_names)
      
        try:
            schema = self._convert_struct_schema("CreateOpts", True)
        except Exception as ex:
            raise Exception("Convert schema failed: %s" % ex)

        fo = None
        try:
            fo = open(resource_file, "a")
            for i in schema:
                fo.writelines(i)

        except Exception as ex:
            raise Exception("Write schema failed: %s" % ex)

        finally:
            if fo:
                fo.close()

    @classmethod
    def _add_desc(cls, structs, doc):
        ret = {}

        for struct_name, struct in structs.items():
            result = []
            doc_struct_map = {item.param: item for item in doc.get(struct_name, [])}
            if doc_struct_map:
                for item in struct:
                    name, _ = cls._parse_req_opt_tag(item.tag)
                    result.append(ParamDef(item.name, item.param_type, item.tag,
                                           doc_struct_map[name].desc))
            else:
                for item in struct:
                    result.append(ParamDef(item.name, item.param_type, item.tag, ""))

            ret[struct_name] = result

        return ret

    def _check_update_create_opts(self, req_structs):
        """all the opts of Update should be the sub set of Create"""
        struct_pair = [("UpdateOpts", "CreateOpts")]

        def _check_struct(ustruct_name, cstruct_name):
            ustruct = req_structs.get(ustruct_name)
            cstruct = req_structs.get(cstruct_name)
            if not ustruct:
                return
            if not cstruct:
                raise Exception("create struct:%s is not exists, but update:%s exists" % (cstruct_name, ustruct_name))

            cstruct_map = {self._parse_req_opt_tag(item.tag)[0]: item for item in cstruct}
            for item in ustruct:
                name, _ = self._parse_req_opt_tag(item.tag)
                if name not in cstruct_map:
                    raise Exception("create opt:%s is not exists, but update exists" % name)

                uti = self._parse_param_type(item, ustruct_name)
                cti = self._parse_param_type(cstruct_map[name], cstruct_name)
                uis = self.is_struct(uti.type_kind)
                cis = self.is_struct(cti.type_kind)
                if not uis and not cis:
                    continue
                if uis and not cis:
                    raise Exception("create opts:%s is a not struct type, but update opt is" % name)
                if not uis and cis:
                    raise Exception("create opts:%s is a struct type, but update opt is not" % name)

                struct_pair.append((uti.go_type, cti.go_type))

        i = 0
        while i < len(struct_pair):
            _check_struct(*struct_pair[i])
            i += 1


    def _merge_structs(self, req_structs, req_head_struct_name, resp_structs, resp_head_struct_name):

        need_merge_structs_pair = [(req_head_struct_name, resp_head_struct_name)]

        def _merge_struct(req_struct_name, resp_struct_name):
            result = []

            resp_struct = resp_structs.get(resp_struct_name, [])
            resp_struct_map = {self._get_tag_item(item.tag, "json"): item for item in resp_struct}

            parsed_params = set()
            req_struct = req_structs[req_struct_name]
            for item in req_struct:
                name, required = self._parse_req_opt_tag(item.tag)
                # this scenario may be exist
                #if name not in resp_struct_map:
                #    raise Exception("req struct:%s opt:%s not in resp struct:%s" % (
                #        req_struct_name, name, resp_struct_name))

                parsed_params.add(name)

                type_info = self._parse_param_type(item, req_struct_name)
                result.append(OptDef(name.lower(), OptKindRequired if required else OptKindOptionalComputed,
                                     type_info, item.desc))

                if self.is_struct(type_info.type_kind):
                    rsn = ""
                    if name in resp_struct_map:
                        rsp_type_info = self._parse_param_type(resp_struct_map[name], resp_struct_name)
                        if not self.is_struct(rsp_type_info.type_kind):
                            raise Exception("req struct:%s, opt:%s is struct, but the corresponding item of resp struct:%s is not" % (
                                req_struct_name, name, resp_struct_name))

                        rsn = rsp_type_info.go_type

                    need_merge_structs_pair.append((type_info.go_type, rsn))

            for name in set(resp_struct_map.keys()) - parsed_params:
                item = resp_struct_map[name]
                type_info = self._parse_param_type(item, resp_struct_name)
                result.append(OptDef(name.lower(), OptKindComputed, type_info, item.desc))

                if self.is_struct(type_info.type_kind):
                    self._parse_resp_struct(resp_structs, type_info.go_type)

            self._structs[req_struct_name] = result

        i = 0
        while i < len(need_merge_structs_pair):
            _merge_struct(*need_merge_structs_pair[i])
            i += 1
           
    def _parse_req_struct(self, req_structs, head_struct_name):
        need_parse_struct_names = [head_struct_name]

        def _parse_single_req_struct(struct_name):
            result = []

            struct = req_structs[struct_name]
            for item in struct:
                name, required = self._parse_req_opt_tag(item.tag)

                type_info = self._parse_param_type(item, struct_name)
                result.append(OptDef(name.lower(), OptKindRequired if required else OptKindOptional,
                                     type_info, item.desc))

                if self.is_struct(type_info.type_kind):
                    need_parse_struct_names.append(type_info.go_type)

            return result

        i = 0
        while i < len(need_parse_struct_names):
            struct_name = need_parse_struct_names[i]
            self._structs[struct_name] = _parse_single_req_struct(struct_name)
            i += 1

    def _parse_resp_struct(self, resp_structs, head_struct_name):
        need_parse_struct_names = [head_struct_name]

        def _parse_single_resp_struct(struct_name):
            result = []

            struct = resp_structs[struct_name]
            for item in struct:
                name = self._get_tag_item(item.tag, "json")
                if not name:
                    raise Exception("Can get json from tag: %s, in resp struct: %s" % (
                                    item.tag, struct_name))

                type_info = self._parse_param_type(item, struct_name)
                result.append(OptDef(name.lower(), OptKindComputed, type_info, item.desc))

                if self.is_struct(type_info.type_kind):
                    need_parse_struct_names.append(type_info.go_type)

            return result

        i = 0
        while i < len(need_parse_struct_names):
            struct_name = need_parse_struct_names[i]
            self._structs[struct_name] = _parse_single_resp_struct(struct_name)
            i += 1

    @classmethod
    def is_struct(cls, kind):
        return kind in [TypeKindStruct, TypeKindStructList]

    def _parse_param_type(self, param, struct_name):
        basic_type_map = {
            "string": "TypeString",
            "int": "TypeInt",
            "bool": "TypeBool"
        }
        param_type = param.param_type

        if param_type in basic_type_map:
            return ParamTypeInfo(TypeKindSimple, param_type, basic_type_map[param_type])

        elif param_type in self._struct_names:
            return ParamTypeInfo(TypeKindStruct, param_type, "TypeList")

        elif re.match("^\[\][a-zA-Z0-9]+$", param_type):
            real_type = param_type[2:]

            if real_type in basic_type_map:
                return ParamTypeInfo(TypeKindSimpleList, real_type, basic_type_map[real_type])

            elif real_type in self._struct_names:
                return ParamTypeInfo(TypeKindStructList, real_type, "TypeList")

        print self._struct_names
        raise Exception("Unknown parameter type: %s for param: %s in struct: %s" % (param_type, param.name, struct_name))

    @classmethod
    def _get_tag_item(cls, tag, item_name):
        m = re.compile('%s:"[^"]*"' % item_name)
        i = m.search(tag)
        if i:
            s = tag[i.start():i.end()]
            return s[s.find('"') + 1:-1]
        return ""

    @classmethod
    def _parse_req_opt_tag(cls, tag):
        required = cls._get_tag_item(tag, "required") == "true"

        j = cls._get_tag_item(tag, "json")
        if not j:
            raise Exception("tag:%s does not include json" % tag)

        return j.split(",")[0], required

    def _convert_struct_schema(self, struct_name, is_top_struct=False):
        schema = []

        opts = self._structs.get(struct_name)
        if not opts:
            raise Exception("Can not find '%s'" % struct_name)

        if not is_top_struct:
            schema.append("Schema: map[string]*schema.Schema{\n")
        for opt in opts:
            opt_schema = self._convert_opt_schema(opt)
            if isinstance(opt_schema, str):
                schema.append(opt_schema)
            else:
                schema.extend(opt_schema)
        schema.append("},\n")

        return schema

    @classmethod
    def _get_param_kind_desc(cls, kind):
        m = {
            OptKindRequired: "Required: true",
            OptKindOptionalComputed: "Optional: true,\nComputed: true",
            OptKindComputed: "Computed: true",
            OptKindOptional: "Optional: true",
        }
        return m.get(kind, "")

    def _convert_opt_schema(self, opt):
        param_kind = self._get_param_kind_desc(opt.opt_kind)
        param_type = opt.param_type_info
        if param_type.type_kind == TypeKindSimple:
            return """"%(schema_name)s": &schema.Schema{
Type:     schema.%(terraform_type)s,
%(param_kind)s,
Default:"",
},
""" %   {   "schema_name": opt.schema_name,
            "terraform_type": param_type.terraform_type,
            "param_kind": param_kind,
        }

        if param_type.type_kind == TypeKindStruct:
            s = """"%(schema_name)s": &schema.Schema{
Type:     schema.TypeList,
%(param_kind)s,
MaxItems: 1,
Elem: &schema.Resource{
""" %       {   "schema_name": opt.schema_name,
                "param_kind": param_kind,
            }

            ret = [s]
            ret.extend(self._convert_struct_schema(param_type.go_type))
            ret.append("},\n},\n")
            return ret

        if param_type.type_kind == TypeKindSimpleList:
            return """"%(schema_name)s": &schema.Schema{
Type:     schema.TypeList,
%(param_kind)s,
MaxItems: 0,
Elem: &schema.Schema{Type: schema.%(terraform_type)s},
},
""" %       {   "schema_name": opt.schema_name,
                "param_kind": param_kind,
                "terraform_type": param_type.terraform_type,
            }

        if param_type.type_kind == TypeKindStructList:
            s = """"%(schema_name)s": &schema.Schema{
Type:     schema.TypeList,
%(param_kind)s,
MaxItems: 0,
Elem: &schema.Resource{
""" %       {   "schema_name": opt.schema_name,
                "param_kind": param_kind,
            }
            ret = [s]
            ret.extend(self._convert_struct_schema(param_type.go_type))
            ret.append("},\n},\n")
            return ret


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print "usage: python convert_to_schema.py resource_name, resource_file, sdk_dir, api_doc_dir, req_struct_names, resp_struct_names"
        print sys.argv
        sys.exit(0)

    ConvertToSchema().run(*sys.argv[1:])

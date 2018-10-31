class Basic(object):
    def __init__(self, param, parent=None):
        self._param_name = param.name
        self._parent_param = parent

        self._items = {
            "Type": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, v),
            },
            "Optional": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },
            "Required": {
                "value": True if param.mandatory == "yes" else None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },
            "Computed": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },
            "description": {
                "value": param.desc,
                "yaml": None,
            },
            "create_update": {
                "value": None,
                "yaml": None,
            },
        }

    def to_schema(self, indent):
        self._set_opertional()

        r = ["%s\"%s\": &schema.Schema{\n" % ('\t' * indent, self._param_name)]

        keys = ["Type", "Required", "Optional", "Computed", "MaxItems", "Elem"]
        i = indent + 1
        for k in keys:
            v = self.get_item(k)
            if v is not None:
                r.append(self._items[k]["yaml"](i, k, v))

        r.append("%s},\n\n" % ('\t' * indent))
        return r

    @staticmethod
    def _indent(indent, key, value):
        return "%s%s: %s,\n" % ("\t" * indent, key, value)

    '''
    def __getattr__(self, key):
        if key in self._items:
            return self._items[k]

        raise AttributeError()
    '''

    def set_item(self, k, v):
        if k in self._items:
            self._items[k]["value"] = v

    def get_item(self, k, default=None):
        return self._items[k]["value"] if k in self._items else default

    @property
    def param_name(self):
        return self._param_name

    def merge(self, other, callback):
        if type(self) != type(other):
            print("merge(%s) on different type:%s ->->->- %s\n" %
                  (self._items['name']['value'], type(other), type(self)))
        else:
            callback(other, self)

    def traverse(self, callback):
        callback(self)

    def _get_ancestor(self):
        if self._parent_param is None:
            return self
        return self._parent_param._get_ancestor()

    def param_doc(self):

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

        head = ""
        a = self._get_ancestor()
        if a.get_item("create_update"):
            head = "* `%s` - (%s) " % (
                self._param_name,
                'Required' if self.get_item("Required") else 'Optional')
        else:
            head = "* `%s` - " % self._param_name

        result = []
        head += self.get_item("description")
        for p in head[4:].split("\n"):
            result.append(_paragraph_yaml(p, 4, 75))
            result.append("\n")

        result.pop()
        result[0] = head[:4] + result[0][4:]
        return "".join(result)

    def _set_opertional(self):
        a = self._get_ancestor()
        if a.get_item("create_update") and not self.get_item("Required"):
            self.set_item("Optional", True)


class MMString(Basic):
    def __init__(self, param, parent=None):
        super(MMString, self).__init__(param, parent)
        self._items["Type"]["value"] = "TypeString"


class MMInteger(Basic):
    def __init__(self, param, parent=None):
        super(MMInteger, self).__init__(param, parent)
        self._items["Type"]["value"] = "TypeInt"


class MMBoolean(Basic):
    def __init__(self, param, parent=None):
        super(MMBoolean, self).__init__(param, parent)
        self._items["Type"]["value"] = "TypeBool"


class MMArray(Basic):
    def __init__(self, param, all_structs, is_single_object=None, parent=None):
        super(MMArray, self).__init__(param, parent)
        self._items["Type"]["value"] = "TypeList"

        self._items["MaxItems"] = {
            "value": None,
            "yaml": lambda n, k, v: self._indent(n, k, v),
        }
        if is_single_object:
            self.set_item("MaxItems", 1)

        v = None
        ptype = param.ptype[2:]
        if ptype == "string":
            v = "&schema.Schema{Type: schema.TypeString}"
        elif ptype in all_structs:
            v = build(all_structs[ptype], all_structs, self)
        elif is_single_object:
            v = build(all_structs[param.ptype], all_structs, self)
        else:
            raise Exception("Convert to MMArray failed, unknown parameter "
                            "type(%s)" % ptype)

        self._items["Elem"] = {
            "value": v,
            "yaml": self._item_type_yaml,
        }

    @staticmethod
    def _item_type_yaml(indent, k, v):
        if not isinstance(v, dict):
            return "%s%s: %s,\n" % ('\t' * indent, k, v)

        r = [
            "%s%s: &schema.Resource{\n" % ('\t' * indent, k),
            "%sSchema: map[string]*schema.Schema{\n" % ('\t' * (indent + 1))
        ]

        i = indent + 2
        keys = sorted(v.keys())
        for k1 in keys:
            r.extend(v[k1].to_schema(i))
        r[-1] = r[-1][:-1]

        r.append("%s},\n" % ('\t' * (indent + 1)))
        r.append("%s},\n" % ('\t' * indent))
        return "".join(r)

    def __getattr__(self, key):
        item_type = self._items["Elem"]["value"]
        if isinstance(item_type, dict) and key in item_type:
            return item_type[key]

        return super(MMArray, self).__getattr__(key)

    def merge(self, other, callback):
        super(MMArray, self).merge(other, callback)

        if not isinstance(other, MMArray):
            return

        self_item_type = self._items["Elem"]["value"]
        if not isinstance(self_item_type, dict):
            return

        other_item_type = other.get_item("Elem")

        for k, v in other_item_type.items():
            if k not in self_item_type:
                self_item_type[k] = v
            else:
                self_item_type[k].merge(v, callback)

        for k, v in self_item_type.items():
            if k not in other_item_type:
                callback(None, v)

    def traverse(self, callback):
        callback(self)

        self_item_type = self._items["Elem"]["value"]
        if not isinstance(self_item_type, dict):
            return

        for k, v in self_item_type.items():
            v.traverse(callback)

    def param_doc_detail(self):
        if not isinstance(self.get_item("Elem"), dict):
            return ""

        child_array = []
        r = ["The `%s` block supports:\n" % self._param_name]
        for _, v in self.get_item("Elem").items():
            r.append("\n%s" % v.param_doc())
            if isinstance(v, MMArray):
                child_array.append(v)

        for v in child_array:
            r.append("\n")
            r.extend(v.param_doc_detail())
        return r


_mm_type_map = {
    "string": MMString,
    "bool": MMBoolean,
    "int": MMInteger,
}


def build(struct, all_structs, parent_param=None):
    r = {}
    for name, p in struct.items():
        ptype = p.ptype
        if ptype in _mm_type_map:
            r[name] = _mm_type_map[ptype](p, parent_param)
        elif ptype in all_structs:
            r[name] = MMArray(p, all_structs, True, parent_param)
        elif ptype.find("[]") == 0:
            r[name] = MMArray(p, all_structs, False, parent_param)
        else:
            raise Exception("Convert to mm object failed, unknown parameter "
                            "type(%s)" % ptype)
    return r

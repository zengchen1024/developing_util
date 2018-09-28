class Basic(object):
    def __init__(self, param):
        self._mm_type = ""

        self._items = {
            "name": {
                "value": param.name,
                "yaml": lambda n, k, v: self._indent(n, k, '\'' + v + '\''),
            },

            "description": {
                "value": param.desc,
                "yaml": self._desc_yaml,
            },

            "exclude": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },

            "output": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },

            "input": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },

            "field": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, '\'' + v + '\''),
            },

            "required": {
                "value": True if param.mandatory == "yes" else None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },

            "update_verb": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, '\'' + v + '\''),
            },

            "update_url": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, '\'' + v + '\''),
            },

            "create_update": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, '\'' + v + '\''),
            },

            "ex_property_opts": {
                "value": None,
                "yaml": None,
            },

        }

    def to_yaml(self, indent):
        keys = self._items.keys().sort()
        r = ["%s- %s\n" % (' '*indent, self._mm_type)]
        indent += 2
        for k in keys:
            v = self._items[k]
            if v["value"] is not None:
                r.append(v["yaml"](indent, k, v["value"]))
        return r

    def _indent(indent, key, value):
        return "%s%s: %s\n" % (" " * indent, key, value)

    '''
    def __getattr__(self, key):
        if key in self._items:
            return self._items[k]

        raise AttributeError()
    '''

    def set_item(self, k, v):
        if k in self._items:
            self._items[k]["value"] = v

    def get_item(self, k):
        return self._items[k]["value"] if k in self._items else None

    def merge(self, other, callback):
        if type(self) != type(other):
            print("merge on different type:%s <--> %s\n" %
                  (type(self), type(other)))
        else:
            callback(other, self)

    def _desc_yaml(self, indent, k, v):
        if indent + len(k) + len(v) + 4 < 80:
            return self._indent(indent, k, "\"%s\"" % v)

        r = ["%s%s: |\n" % (' ' * indent, k)]
        indent += 2

        l = 79 - indent
        if l < 20:
            l = 20
        s1 = v
        while s1:
            i = s1.rfind(" ", 0, l)
            s2, s1 = (s1[:l], s1[l:]) if i == -1 else (s1[:i], s1[(i + 1):])
            r.append("%s%s\n" % (' ' * indent, s2))
        return r


class MMString(Basic):
    def __init__(self, param):
        super(MMString, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::String"


class MMInteger(Basic):
    def __init__(self, param):
        super(MMInteger, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::Integer"


class MMBoolean(Basic):
    def __init__(self, param):
        super(MMBoolean, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::Boolean"


class MMNestedObject(Basic):
    def __init__(self, param, struct, all_structs):
        super(MMNestedObject, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::NestedObject"

        self._items["properties"] = {
            "value": build(struct, all_structs),
            "yaml": self._properties_yaml,
        }

    @staticmethod
    def _properties_yaml(indent, k, v):
        r = ["%s%s:\n" % (' ' * indent, k)]
        keys = v.keys().sort()
        indent += 2
        for k1 in keys():
            r.extend(v[k1].to_yaml(indent))

    def __getattr__(self, key):
        p = self._items["properties"]["value"]
        if key in p:
            return p[key]

        return super(MMArray, self).__getattr__(key)

    def merge(self, other, callback):
        super(MMNestedObject, self).merge(other)

        if not isinstance(other, MMNestedObject):
            return

        self_properties = self._items["properties"]["value"]
        other_properties = other.get_item("properties")
        for k, v in other_properties.items():
            if k not in self_properties:
                self_properties[k] = v
            else:
                callback(v, self_properties[k])

        for k, v in self_properties.items():
            if k not in other_properties:
                callback(None, v)


class MMArray(Basic):
    def __init__(self, param, all_structs):
        super(MMArray, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::Array"

        v = None
        ptype = param.ptype[2:]
        if ptype == "string":
            v = "Api::Type::String"
        elif ptype in all_structs:
            v = build(all_structs[ptype], all_structs)
        else:
            raise Exception("Convert to MMArray failed, unknown parameter "
                            "type(%s)" % ptype)

        self._items["item_type"] = {
            "value": v,
            "yaml": self._item_type_yaml,
        }

        self._items["max_size"] = {
            "value": None,
            "yaml": lambda n, k, v: self._indent(n, k, str(v)),
        }

    @staticmethod
    def _item_type_yaml(indent, k, v):
        if isinstance(v, str):
            return ["%s%s: %s\n" % (' ' * indent, k, v)]

        r = [
            "%s%s: !ruby/object:Api::Type::NestedObject\n" % (' ' * indent, k),
            "%sproperties:\n" % ' ' * (indent + 2)
        ]
        keys = v.keys().sort()
        indent += 4
        for k1 in keys():
            r.extend(v[k1].to_yaml(indent))

    def __getattr__(self, key):
        item_type = self._items["item_type"]["value"]
        if isinstance(item_type, dict) and key in item_type:
            return item_type[key]

        return super(MMArray, self).__getattr__(key)

    def merge(self, other, callback):
        super(MMArray, self).merge(other)

        if not isinstance(other, MMArray):
            return

        self_item_type = self._items["item_type"]["value"]
        other_item_type = other.get_item("item_type")
        for k, v in other_item_type.items():
            if k not in self_item_type:
                self_item_type[k] = v
            else:
                callback(v, self_item_type[k])

        for k, v in self_item_type.items():
            if k not in other_item_type:
                callback(None, v)


_mm_type_map = {
    "string": MMString,
    "bool": MMBoolean,
    "int": MMInteger
}


def build(struct, all_structs):
    r = {}
    for name, p in struct.items():
        ptype = p.ptype
        if ptype in _mm_type_map:
            r[name] = _mm_type_map[ptype](p)
        elif ptype in all_structs:
            r[name] = MMNestedObject(all_structs[ptype], all_structs)
        elif ptype.find("[]") == 0:
            r[name] = MMArray(p, all_structs)
        else:
            raise Exception("Convert to mm object failed, unknown parameter "
                            "type(%s)" % ptype)
    return r

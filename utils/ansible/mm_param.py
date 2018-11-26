Merge_Level = (
    Merge_Level_Root,
    Merge_Level_Child
) = (
    "root",
    "child"
)


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

            "is_id": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, str(v).lower()),
            },
        }

    def to_yaml(self, indent):
        keys = self._items.keys()
        keys.remove("name")
        keys.remove("description")
        keys.sort()
        keys.insert(0, "name")
        keys.insert(1, "description")

        r = ["%s- %s\n" % (' ' * indent, self._mm_type)]
        indent += 2
        for k in keys:
            v = self._items[k]
            if v["value"] is not None:
                r.append(v["yaml"](indent, k, v["value"]))
        return r

    @staticmethod
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

    def get_item(self, k, default=None):
        return self._items[k]["value"] if k in self._items else default

    def merge(self, other, callback, level):
        if type(self) != type(other):
            print("merge(%s) on different type:%s ->->->- %s\n" %
                  (self._items['name']['value'], type(other), type(self)))
        else:
            callback(other, self, level)

    def traverse(self, callback):
        callback(self)

    def _desc_yaml(self, indent, k, v):
        if indent + len(k) + len(v) + 4 < 80:
            return self._indent(indent, k, "\"%s\"" % v)

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

        result = ["%s%s: |\n" % (' ' * indent, k)]
        indent += 2
        max_len = 79 - indent
        if max_len < 20:
            max_len = 20

        for p in v.split("\n"):
            result.append(_paragraph_yaml(p, indent, max_len))
            result.append("\n")

        result.pop()
        return "".join(result)


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


class MMTime(Basic):
    def __init__(self, param):
        super(MMTime, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::Time"


class MMNameValues(Basic):
    def __init__(self, param):
        super(MMNameValues, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::NameValues"

        self._items.update({
            "key_type": {
                "value": "Api::Type::String",
                "yaml": lambda n, k, v: self._indent(n, k, v),
            },
            "value_type": {
                "value": "Api::Type::String",
                "yaml": lambda n, k, v: self._indent(n, k, v),
            }
        })


class MMEnum(Basic):
    def __init__(self, param, values=[]):
        super(MMEnum, self).__init__(param)
        self._mm_type = "!ruby/object:Api::Type::Enum"

        self._items.update({
            "values": {
                "value": values,
                "yaml": self._values_yaml,
            },
            "element_type": {
                "value": None,
                "yaml": lambda n, k, v: self._indent(n, k, v),
            }
        })

    @staticmethod
    def _values_yaml(indent, k, v):
        r = ["%s%s:\n" % (' ' * indent, k)]
        indent += 2
        for i in v:
            r.append("%s- :%s\n" % (' ' * indent, str(i)))
        return "".join(r)


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
        keys = sorted(v.keys())
        indent += 2
        for k1 in keys:
            r.extend(v[k1].to_yaml(indent))
        return "".join(r)

    def __getattr__(self, key):
        p = self._items["properties"]["value"]
        if key in p:
            return p[key]

        return super(MMArray, self).__getattr__(key)

    def merge(self, other, callback, level):
        super(MMNestedObject, self).merge(other, callback, level)

        if not isinstance(other, MMNestedObject):
            return

        self_properties = self._items["properties"]["value"]
        other_properties = other.get_item("properties")
        for k, v in other_properties.items():
            if k not in self_properties:
                print("run %s on opt(%s), right is None\n" %
                    (callback.__name__, v.get_item('name')))

                callback(v, None, Merge_Level_Child)
                self_properties[k] = v
            else:
                self_properties[k].merge(v, callback, Merge_Level_Child)

        for k, v in self_properties.items():
            if k not in other_properties:
                print("run %s on opt(%s), left is None\n" %
                    (callback.__name__, v.get_item('name')))

                callback(None, v, Merge_Level_Child)

    def traverse(self, callback):
        callback(self)

        for k, v in self._items["properties"]["value"].items():
            v.traverse(callback)


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
            return "%s%s: %s\n" % (' ' * indent, k, v)

        r = [
            "%s%s: !ruby/object:Api::Type::NestedObject\n" % (' ' * indent, k),
            "%sproperties:\n" % (' ' * (indent + 2))
        ]
        keys = sorted(v.keys())
        indent += 4
        for k1 in keys:
            r.extend(v[k1].to_yaml(indent))
        return "".join(r)

    def __getattr__(self, key):
        item_type = self._items["item_type"]["value"]
        if isinstance(item_type, dict) and key in item_type:
            return item_type[key]

        return super(MMArray, self).__getattr__(key)

    def merge(self, other, callback, level):
        super(MMArray, self).merge(other, callback, level)

        if not isinstance(other, MMArray):
            return

        self_item_type = self._items["item_type"]["value"]
        if isinstance(self_item_type, str):
            return

        other_item_type = other.get_item("item_type")
        for k, v in other_item_type.items():
            if k not in self_item_type:
                print("run %s on opt(%s), right is None\n" %
                    (callback.__name__, v.get_item('name')))

                callback(v, None, Merge_Level_Child)
                self_item_type[k] = v
            else:
                self_item_type[k].merge(v, callback, Merge_Level_Child)

        for k, v in self_item_type.items():
            if k not in other_item_type:
                print("run %s on opt(%s), left is None\n" %
                    (callback.__name__, v.get_item('name')))

                callback(None, v, Merge_Level_Child)

    def traverse(self, callback):
        callback(self)

        self_item_type = self._items["item_type"]["value"]
        if isinstance(self_item_type, str):
            return

        for k, v in self_item_type.items():
            v.traverse(callback)


_mm_type_map = {
    "string": MMString,
    "bool": MMBoolean,
    "int": MMInteger,
    "time": MMTime,
    "enum": MMEnum,
    "map": MMNameValues,
}


def build(struct, all_structs):
    r = {}
    for name, p in struct.items():
        ptype = p.ptype
        if ptype in _mm_type_map:
            r[name] = _mm_type_map[ptype](p)
        elif ptype in all_structs:
            r[name] = MMNestedObject(p, all_structs[ptype], all_structs)
        elif ptype.find("[]") == 0:
            r[name] = MMArray(p, all_structs)
        else:
            raise Exception("Convert to mm object failed, unknown parameter "
                            "type(%s)" % ptype)
    return r

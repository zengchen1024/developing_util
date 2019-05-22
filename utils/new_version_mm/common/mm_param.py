import re


Merge_Level = (
    Merge_Level_Root,
    Merge_Level_Child
) = (
    "root",
    "child"
)


def _indent(indent, key, value):
    return "%s%s: %s\n" % (" " * indent, key, value)


class Basic(object):
    def __init__(self):
        self._mm_type = ""
        self._parent = None
        self._path = dict()
        self._alias = ""

        self._items = {
            "name": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, '\'' + v + '\''),
            },

            "description": {
                "value": None,
                "yaml": self._desc_yaml,
                "param_yaml": self._desc_yaml
            },

            "exclude": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "output": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "field": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, '\'' + v + '\''),
            },

            "required": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "crud": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, "\'%s\'" % v),
            },

            "default": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, "%s" % v),
            },

            "is_id": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "send_empty_value": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "alone_parameter": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "array_num": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, v),
            },
        }

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, p):
        self._parent = p

    @property
    def path(self):
        return self._path

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, value):
        self._alias = value

    @property
    def real_type(self):
        s = self._mm_type
        return s[s.find(":") + 1:]

    def init(self, param, parent):
        self._parent = parent

        self.set_item("name", param["name"])

        desc = param.get("description")
        if desc:
            self.set_item("description", desc.strip("\n"))

        if param["mandatory"]:
            self.set_item("required", True)

        if "alias" in param:
            self._alias = param["alias"]

        return self

    def to_yaml(self, indent):
        if self.get_item("exclude"):
            return

        keys = self._items.keys()
        keys.remove("name")
        keys.remove("description")
        keys.sort()
        keys.insert(0, "name")
        keys.insert(1, "description")

        r = ["%s- %s\n" % (' ' * indent, self._mm_type)]
        indent += 2
        for k in keys:
            v = self.get_item(k)
            if v:
                r.append(self._items[k]["yaml"](indent, k, v))

        return r

    def to_param_yaml(self, indent):
        if self.get_item("exclude"):
            return

        name = self.alias if self.alias else self.get_item("name")
        r = [
            "%s%s:\n" % (' ' * indent, name),
            "%sdatatype: %s\n" % (' ' * (indent + 2),
                                  self._mm_type.split(":")[-1])
        ]
        for k, v in self._path.items():
            if v:
                r.append("%s%s: %s\n" % (' ' * (indent + 2), k, v))

        keys = self._items.keys()
        keys.sort()

        indent += 2
        for k in keys:
            v = self._items[k]
            val = v["value"]
            f = v.get("param_yaml")
            if val and f:
                s = f(indent, k, val)
                if s:
                    r.append(s)
        return r

    def set_item(self, k, v):
        if k in self._items:
            self._items[k]["value"] = v

    def get_item(self, k, default=None):
        return self._items[k]["value"] if k in self._items else default

    def merge(self, other, callback, level):
        if self.real_type != other.real_type:
            print("merge(%s) on different type:%s ->->->- %s\n" %
                  (self.get_item('name'), type(other), type(self)))

            raise Exception("Can't merge on different type")

        else:
            callback(other, self, level)

    def traverse(self, callback):
        callback(self)

    def post_traverse(self, callback):
        callback(self, leaf=True)

    def child(self, key):
        raise Exception("Unsupported method of child")

    def childs(self):
        raise Exception("Unsupported method of childs")

    def add_child(self, child):
        raise Exception("Unsupported method of add_child")

    def delete_child(self, child):
        raise Exception("Unsupported method of delete_child")

    def _desc_yaml(self, indent, k, v):
        v = v.strip().strip("\n")
        if indent + len(k) + len(v) + 4 < 80:
            return _indent(indent, k, "\"%s\"" % v)

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

        for p in re.split(r"^\n", v):
            result.append(
                _paragraph_yaml(p.replace("\n", " "), indent, max_len))
            result.append("\n")

        result.pop()
        return "".join(result)


class MMString(Basic):
    def __init__(self):
        super(MMString, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::String"


class MMInteger(Basic):
    def __init__(self):
        super(MMInteger, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Integer"

        self._items["default"]["yaml"] = (
            lambda n, k, v: _indent(n, k, str(v)))


class MMBoolean(Basic):
    def __init__(self):
        super(MMBoolean, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Boolean"

        self._items["default"]["yaml"] = (
            lambda n, k, v: _indent(n, k, str(v).lower()))


class MMTime(Basic):
    def __init__(self):
        super(MMTime, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Time"


class MMNameValues(Basic):
    def __init__(self):
        super(MMNameValues, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::NameValues"

        self._items.update({
            "key_type": {
                "value": "Api::Type::String",
                "yaml": lambda n, k, v: _indent(n, k, v),
            },
            "value_type": {
                "value": "Api::Type::String",
                "yaml": lambda n, k, v: _indent(n, k, v),
            }
        })

    def init(self, param, parent):
        super(MMNameValues, self).init(param, parent)

        m = re.match(r"dict\((.*),(.*)\)", param["datatype"])
        if not m:
            raise Exception("Convert to MMNameValues failed, unknown "
                            "parameter type(%s) for parameter(%s)" % (
                                param["datatype"], param["name"]))

        kt = m.group(1).strip()
        vt = m.group(2).strip()
        if kt != "str" or vt != "str":
            raise Exception("Convert to MMNameValues failed, unknown "
                            "parameter type(%s) for parameter(%s). The type "
                            "of key and value must be str" % (
                                param["datatype"], param["name"]))
        return self


class MMEnum(Basic):
    def __init__(self):
        super(MMEnum, self).__init__()

        self._mm_type = "!ruby/object:Api::Type::Enum"

        self._items.update({
            "values": {
                "value": None,
                "yaml": self._values_yaml,
            },
            "element_type": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, v),
            }
        })

    @property
    def real_type(self):
        return self.get_item("element_type")

    @staticmethod
    def _values_yaml(indent, k, v):
        r = ["%s%s:\n" % (' ' * indent, k)]
        indent += 2
        for i in v:
            r.append("%s- :%s\n" % (' ' * indent, str(i)))
        return "".join(r)

    def init(self, param, parent):
        super(MMEnum, self).init(param, parent)

        v = param.get("allowed_values")
        if v:
            self.set_item("values", v)

        v = param.get("element_type")
        if v:
            element_type = {
                "str": "Api::Type::String",
                "int": "Api::Type::Integer"
            }

            if v not in element_type:
                raise Exception("Convert to MMEnum failed, "
                                "unknown element type(%s)" % v)

            self.set_item("element_type", element_type[v])

        return self


class MMNestedObject(Basic):
    def __init__(self):
        super(MMNestedObject, self).__init__()

        self._mm_type = "!ruby/object:Api::Type::NestedObject"

        self._items["properties"] = {
            "value": None,
            "yaml": self._properties_yaml,
            "param_yaml": self._properties_param_yaml
        }

    def add_child(self, key, child):
        v = self.get_item("properties")
        if v is None:
            v = {}
            self.set_item("properties", v)

        v[key] = child
        child.parent = self

    def delete_child(self, key):
        v = self.get_item("properties")
        v.pop(key)

    def init(self, param, parent, all_structs, build):
        super(MMNestedObject, self).init(param, parent)

        self.set_item("properties",
                      build(all_structs[param["datatype"]], self))

        return self

    @staticmethod
    def _properties_yaml(indent, k, v):
        r = ["%s%s:\n" % (' ' * indent, k)]
        keys = sorted(v.keys())
        indent += 2
        for k1 in keys:
            s = v[k1].to_yaml(indent)
            if s:
                r.extend(s)
        return "".join(r)

    @staticmethod
    def _properties_param_yaml(indent, k, v):
        r = ["%sproperties:\n" % (' ' * indent)]
        keys = sorted(v.keys())
        indent += 2
        for k1 in keys:
            s = v[k1].to_param_yaml(indent)
            if s:
                r.extend(s)
        return "".join(r)

    def child(self, key):
        p = self.get_item("properties")
        if isinstance(p, dict) and key in p:
            return p[key]

        raise Exception(
            "parent:%s, no child with key(%s)" % (self.get_item("name"), key))

    def childs(self):
        p = self.get_item("properties")
        if isinstance(p, dict):
            return p.values()

        raise Exception("no childs for nested object")

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
                v.parent = self
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

    def post_traverse(self, callback):
        for k, v in self._items["properties"]["value"].items():
            v.post_traverse(callback)

        callback(self, leaf=False)


class MMArray(Basic):
    def __init__(self):
        super(MMArray, self).__init__()

        self._mm_type = "!ruby/object:Api::Type::Array"

        self._items["item_type"] = {
            "value": None,
            "yaml": self._item_type_yaml,
            "param_yaml": self._item_type_param_yaml
        }

        self._items["max_size"] = {
            "value": None,
            "yaml": lambda n, k, v: _indent(n, k, str(v)),
        }

    def add_child(self, key, child):
        v = self.get_item("item_type")
        if v is None:
            v = {}
            self.set_item("item_type", v)

        v[key] = child
        child.parent = self

    def delete_child(self, key):
        v = self.get_item("item_type")
        v.pop(key)

    def init(self, param, parent, all_structs, build):
        super(MMArray, self).init(param, parent)

        supported_sub_datatype = {
            "str": "Api::Type::String",
            "int": "Api::Type::Integer"
        }

        sub_datatype = re.match(r"list\[(.*)\]", param["datatype"]).group(1)

        if sub_datatype in supported_sub_datatype:
            self.set_item("item_type", supported_sub_datatype[sub_datatype])

        elif sub_datatype in all_structs:
            self.set_item("item_type",
                          build(all_structs[sub_datatype], self))

        else:
            raise Exception("Convert to MMArray failed, unknown parameter "
                            "type(%s) for parameter(%s)" % (
                                sub_datatype, param["name"]))

        return self

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
            s = v[k1].to_yaml(indent)
            if s:
                r.extend(s)
        return "".join(r)

    @staticmethod
    def _item_type_param_yaml(indent, k, v):
        if isinstance(v, str):
            return None

        r = ["%sproperties:\n" % (' ' * indent)]
        keys = sorted(v.keys())
        indent += 2
        for k1 in keys:
            s = v[k1].to_param_yaml(indent)
            if s:
                r.extend(s)
        return "".join(r)

    def child(self, key):
        item_type = self.get_item("item_type")
        if isinstance(item_type, dict) and key in item_type:
            return item_type[key]

        raise Exception(
            "parent:%s, no child with key(%s)" % (self.get_item("name"), key))

    def childs(self):
        item_type = self.get_item("item_type")
        if isinstance(item_type, dict):
            return item_type.values()

        raise Exception("no childs for array that item type is not a struct")

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
                v.parent = self
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

    def post_traverse(self, callback):
        self_item_type = self._items["item_type"]["value"]
        if isinstance(self_item_type, dict):
            for k, v in self_item_type.items():
                v.post_traverse(callback)

        callback(self, leaf=isinstance(self_item_type, str))


def build(struct, all_structs, index_method, parent=None):

    _mm_type_map = {
        "str": MMString,
        "bool": MMBoolean,
        "int": MMInteger,
        "time": MMTime,
        "enum": MMEnum,
        "map": MMNameValues,
        "datetime": MMTime,
        "date": MMTime,
    }

    def _build(struct1, parent):
        r = {}
        for p in struct1:
            i = index_method(p)
            datatype = p["datatype"]

            if datatype in _mm_type_map:
                r[i] = _mm_type_map[datatype]().init(p, parent)

            elif datatype in all_structs:
                r[i] = MMNestedObject().init(p, parent, all_structs, _build)

            elif datatype.find("list") == 0:
                r[i] = MMArray().init(p, parent, all_structs, _build)

            elif datatype.find("dict") == 0:
                r[i] = MMNameValues().init(p, parent)

            else:
                raise Exception("Convert to mm object failed, unknown "
                                "parameter type(%s) for "
                                "parameter(%s)" % (datatype, p["name"]))
        return r

    return _build(struct, parent)

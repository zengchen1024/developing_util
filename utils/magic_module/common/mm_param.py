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

        self._items = {
            "name": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, '\'' + v + '\''),
            },

            "description": {
                "value": None,
                "yaml": self._desc_yaml,
            },

            "exclude": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "output": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "input": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "field": {
                "value": {
                    "create": None,
                    "update": None,
                    "read": None,
                },
                "yaml": self._field_yaml,
            },

            "required": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, str(v).lower()),
            },

            "update_verb": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, '\'' + v + '\''),
            },

            "update_url": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, '\'' + v + '\''),
            },

            "crud": {
                "value": None,
                "yaml": lambda n, k, v: _indent(n, k, "\'%s\'" % v),
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
        }

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, p):
        self._parent = p

    def init(self, param, parent):
        self._parent = parent

        self.set_item("name", param["name"])

        desc = param.get("description")
        if desc:
            self.set_item("description", desc.strip("\n"))

        if param["mandatory"]:
            self.set_item("required", True)

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
            v = None

            if k == "crud":
                v = self._crud()

            else:
                v = self.get_item(k)

            if v:
                r.append(self._items[k]["yaml"](indent, k, v))

        return r

    def to_param_yaml(self, indent):
        if self.get_item("exclude"):
            return

        r = [
            "%s%s:\n" % (' ' * indent, self.get_item("name")),
        ]
        for k, v in self.get_item("field").items():
            if v:
                r.append("%s%s: %s\n" % (' ' * (indent + 2), k, v))

        keys = self._items.keys()
        keys.sort()

        indent += 2
        for k in keys:
            v = self._items[k]
            if v.get("param_yaml") is not None:
                s = v["param_yaml"](indent, k, v["value"])
                if s:
                    r.append(s)
        return r

    def set_item(self, k, v):
        if k in self._items:
            if k == "field":
                self._set_field(v)
            else:
                self._items[k]["value"] = v

    def get_item(self, k, default=None):
        if k == "crud":
            return self._crud()

        return self._items[k]["value"] if k in self._items else default

    def merge(self, other, callback, level):
        if type(self) != type(other):
            print("merge(%s) on different type:%s ->->->- %s\n" %
                  (self.get_item('name'), type(other), type(self)))

            raise Exception("Can't merge on different type")

        else:
            callback(other, self, level)

    def traverse(self, callback):
        callback(self)

    def child(self, key):
        raise Exception("Unsupported method of child")

    def childs(self):
        raise Exception("Unsupported method of childs")

    def add_child(self, child):
        raise Exception("Unsupported method of add_child")

    def delete_child(self, child):
        raise Exception("Unsupported method of delete_child")

    def _desc_yaml(self, indent, k, v):
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

        for p in v.split("\n"):
            result.append(_paragraph_yaml(p, indent, max_len))
            result.append("\n")

        result.pop()
        return "".join(result)

    def _field_yaml(self, indent, k, v):

        if not any(v.values()):
            raise Exception("The field property of parameter(%s) is "
                            "None" % self.get_item("name"))

        r = ["%s%s:" % (' ' * indent, k),]
        indent += 2

        for k1 in ["create", "update", "read"]:
            v1 = v[k1]
            if v1:
                r.append("%s%s: %s" % (' ' * indent, k1, v1))

        return "\n".join(r) + "\n"

    def _set_field(self, v):
        if not isinstance(v, dict):
            raise Exception("Set field of parameter(%s) failed, the argument "
                            "should be a dict" % self.get_item("name"))

        r = set(v.keys()) - set(["create", "update", "read"])
        if r:
            raise Exception("Set field of parameter(%s) failed, "
                            "unspport field(%s)" % (
                                self.get_item("name"), " ".join(r)))

        self._items["field"]["value"].update(v)

    def _crud(self):
        r = [k[0] for k, v in self.get_item("field").items() if v]
        return "".join(r) if r else ""


class MMString(Basic):
    def __init__(self):
        super(MMString, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::String"

    def clone(self):
        return self.__class__()


class MMInteger(Basic):
    def __init__(self):
        super(MMInteger, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Integer"

    def clone(self):
        return self.__class__()


class MMBoolean(Basic):
    def __init__(self):
        super(MMBoolean, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Boolean"

    def clone(self):
        return self.__class__()


class MMTime(Basic):
    def __init__(self):
        super(MMTime, self).__init__()
        self._mm_type = "!ruby/object:Api::Type::Time"

    def clone(self):
        return self.__class__()


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

    def clone(self):
        return self.__class__()

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

    def clone(self):
        i = self.__class__()
        i.set_item("values", self.get_item("values"))
        i.set_item("element_type", self.get_item("element_type"))

        return i

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

    def clone(self):
        return self.__class__()

    def add_child(self, child):
        v = self.get_item("properties")
        if v is None:
            v = {}
            self.set_item("properties", v)

        v[child.get_item("name")] = child

    def delete_child(self, child):
        v = self.get_item("properties")
        v.pop(child.get_item("name"))

    def init(self, param, parent, all_structs):
        super(MMNestedObject, self).init(param, parent)

        self.set_item("properties",
                      build(all_structs[param["datatype"]], all_structs, self))

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

        raise Exception("no child with key(%s)" % key)

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

    def clone(self):
        i = self.__class__()

        v = self.get_item("item_type")
        if isinstance(v, str):
            i.set_item("item_type", v)

        return i

    def add_child(self, child):
        v = self.get_item("item_type")
        if v is None:
            v = {}
            self.set_item("item_type", v)

        v[child.get_item("name")] = child

    def delete_child(self, child):
        v = self.get_item("item_type")
        v.pop(child.get_item("name"))

    def init(self, param, parent, all_structs):
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
                          build(all_structs[sub_datatype], all_structs, self))

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

        raise Exception("no child with key(%s)" % key)

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
    "str": MMString,
    "bool": MMBoolean,
    "int": MMInteger,
    "time": MMTime,
    "enum": MMEnum,
    "map": MMNameValues,
    "datetime": MMTime,
    "date": MMTime,
}


def build(struct, all_structs, parent=None):
    r = {}
    for p in struct:
        name = p["name"]
        datatype = p["datatype"]

        if datatype in _mm_type_map:
            r[name] = _mm_type_map[datatype]().init(p, parent)

        elif datatype in all_structs:
            r[name] = MMNestedObject().init(p, parent, all_structs)

        elif datatype.find("list") == 0:
            r[name] = MMArray().init(p, parent, all_structs)

        elif datatype.find("dict") == 0:
            r[name] = MMNameValues().init(p, parent)

        else:
            raise Exception("Convert to mm object failed, unknown parameter "
                            "type(%s) for parameter(%s)" % (datatype, name))
    return r

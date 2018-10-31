from collections import namedtuple
import re

ParamDef = namedtuple("ParamDef", "name, param_type, tag")


class RequestStruct(object):

    @classmethod
    def get_struct_def(cls, go_file, all_struct_name):
        result = {}
        f = None
        try:
            end = re.compile("^}\n$")

            i = 0
            sn = all_struct_name[i]
            start = re.compile("^type %s struct {\n$" % sn)
            find_start = False
            struct = []

            f = open(go_file, 'r')
            for l in f:
                if not find_start:
                    if start.match(l):
                        find_start = True
                    continue

                if end.match(l):
                    result[sn] = struct

                    i += 1
                    if i >= len(all_struct_name):
                        break

                    
                    sn = all_struct_name[i]
                    start = re.compile("^type %s struct {\n$" % sn)
                    find_start = False
                    struct = []

                tag_pos = l.find("`")
                if tag_pos == -1:
                    continue

                tag = l[tag_pos:-1]
                name, param_type = l[0:tag_pos].strip().split()
                pd = ParamDef(name.strip(), param_type.strip(), tag)
                struct.append(pd)

        except Exception as ex:
            raise Exception("Read: %s failed: %s" % (go_file, ex))

        finally:
            if f:
                f.close()

        return result

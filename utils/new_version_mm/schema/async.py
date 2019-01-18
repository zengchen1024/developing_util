from common.utils import remove_none


class Async(object):
    def __init__(self, operation, config):
        self._op = operation
        self._query = _Query(config.get("query"))
        self._error = ""
        self._status = ""

    def to_map(self):
        v = {
            "operation": self._op,
            "query": self._query.to_map(),
        }

        return remove_none(v)


class _Query(object):
    def __init__(self, config):
        self._url = config.get("url")
        self._parameters = config.get("parameters", {})
        self._interval_ms = config.get("interval_ms")
        self._service_type = config.get("service_type")

    def to_map(self):
        v = {
            "url": self._url,
            "interval_ms": self._interval_ms,
            "service_type": self._service_type,
        }

        if self._parameters:
            v2 = []
            for k, v1 in self._parameters.items():
                v2.append({
                    "parameter": k,
                    "path": v1
                })
            v.update({
                "has_path_parameter": True,
                "path_parameters": v2
            })

        return remove_none(v)

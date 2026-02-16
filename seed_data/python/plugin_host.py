class Plugin:
    name = "base"

    def execute(self, payload: dict) -> dict:
        raise NotImplementedError

class TimestampPlugin(Plugin):
    name = "timestamp"

    def execute(self, payload: dict) -> dict:
        payload["ts"] = "2026-01-01T00:00:00Z"
        return payload

class PluginHost:
    def __init__(self):
        self.plugins = []

    def register(self, plugin: Plugin):
        self.plugins.append(plugin)

    def dispatch(self, payload: dict) -> dict:
        for plugin in self.plugins:
            payload = plugin.execute(payload)
        return payload

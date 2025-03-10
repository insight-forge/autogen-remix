import os

class PluginService:

    def __init__(self):
        self._basedir = os.path.dirname(os.path.abspath(__file__))
        self._plugins = []
        self.load_plugins()

    def load_plugins(self):
        for dir in os.listdir(self._basedir):
            if dir.startswith('func_'):
                with open(os.path.join(self._basedir, dir), mode="r", encoding="utf-8") as py_file:
                    py_code = py_file.read()
                output = {}
                exec(py_code, {}, output)
                assert "func" in output and "meta_info" in output
                self._plugins.append(output)


def get_plugin_service() -> PluginService:
    return PluginService()
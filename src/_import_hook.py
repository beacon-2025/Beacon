import sys, json, zlib, base64
from pathlib import Path
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec


class RuntimeCompiledLoader(Loader):
    def __init__(self, module_name, module_info):
        self.module_name = module_name
        self.module_info = module_info

    def create_module(self, spec):
        0

    def exec_module(self, module):
        source_code = self._deobfuscate_source(self.module_info["source"])
        module.__file__ = self.module_info.get(
            "filename", f"<compiled>/{self.module_name}.py"
        )
        module.__loader__ = self
        if self.module_info.get("is_package"):
            module.__package__ = self.module_name
            package_path = Path(__file__).parent / self.module_name.replace(".", "/")
            if package_path.exists() and package_path.is_dir():
                module.__path__ = [str(package_path)]
            else:
                module.__path__ = []
        else:
            module.__package__ = self.module_name.rpartition(".")[0]
        code_obj = compile(source_code, module.__file__, "exec")
        exec(code_obj, module.__dict__)

    def _deobfuscate_source(
        self, encoded_source: str, key: bytes = b"PrivilegeGriffin"
    ) -> str:
        obfuscated = base64.b64decode(encoded_source.encode("ascii"))
        compressed = bytes(b ^ key[i % len(key)] for (i, b) in enumerate(obfuscated))
        source_code = zlib.decompress(compressed).decode("utf-8")
        return source_code


class RuntimeCompiledFinder(MetaPathFinder):
    def __init__(self):
        self.modules = {}
        self._load_modules()

    def _load_modules(self):
        data_file = Path(__file__).parent / "_compiled_modules.dat"
        if not data_file.exists():
            return
        try:
            with open(data_file, "rb") as f:
                encrypted_data = f.read()
            json_str = self._decrypt_data(encrypted_data)
            data = json.loads(json_str)
            self.modules = data.get("modules", {})
        except Exception as e:
            print(f"Warning: cannot load module data: {e}")
            self.modules = {}

    def _decrypt_data(
        self, encrypted_data: bytes, key: bytes = b"Griffin2025SecretKey"
    ) -> str:
        magic = encrypted_data[:4]
        if magic != b"PGRF":
            raise ValueError("Invalid data format")
        version = encrypted_data[4:6]
        encrypted = encrypted_data[6:]
        decrypted = bytes(b ^ key[i % len(key)] for (i, b) in enumerate(encrypted))
        decompressed = zlib.decompress(decrypted)
        return decompressed.decode("utf-8")

    def find_spec(self, fullname, path, target=None):
        if fullname in self.modules:
            is_package = self.modules[fullname].get("is_package", False)
            return ModuleSpec(
                fullname,
                RuntimeCompiledLoader(fullname, self.modules[fullname]),
                origin="runtime_compiled",
                is_package=is_package,
            )


_finder = RuntimeCompiledFinder()
if _finder not in sys.meta_path:
    sys.meta_path.insert(0, _finder)

"""Windows Registry skill pack — read/write registry keys with safety checks."""

from tools.base_tool import BaseTool


class RegistryReadTool(BaseTool):
    name = "registry_read"
    description = "Read a Windows registry key or value. Safe read-only operation."
    parameters = {"type": "object", "properties": {
        "key_path": {"type": "string", "description": "Registry path, e.g. HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"},
        "value_name": {"type": "string", "default": "", "description": "Specific value name (empty = list all values)"},
    }, "required": ["key_path"]}

    def run(self, key_path: str, value_name: str = "") -> str:
        try:
            import winreg
            hive, subkey = self._parse_key(key_path)
            if hive is None:
                return f"Invalid hive in path: {key_path}"

            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)

            if value_name:
                value, reg_type = winreg.QueryValueEx(key, value_name)
                winreg.CloseKey(key)
                type_name = self._type_name(reg_type)
                return f"{value_name} ({type_name}) = {value}"
            else:
                # List all values
                lines = [f"Key: {key_path}"]
                i = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, i)
                        type_name = self._type_name(reg_type)
                        val_str = str(value)[:100]
                        lines.append(f"  {name} ({type_name}) = {val_str}")
                        i += 1
                    except OSError:
                        break

                # List subkeys
                subkeys = []
                i = 0
                while True:
                    try:
                        subkeys.append(winreg.EnumKey(key, i))
                        i += 1
                    except OSError:
                        break
                if subkeys:
                    lines.append(f"\nSubkeys ({len(subkeys)}):")
                    for sk in subkeys[:30]:
                        lines.append(f"  {sk}")

                winreg.CloseKey(key)
                return "\n".join(lines)
        except FileNotFoundError:
            return f"Registry key not found: {key_path}"
        except PermissionError:
            return f"Access denied to: {key_path}. May need admin privileges."
        except Exception as e:
            return f"Error: {e}"

    def _parse_key(self, path: str):
        import winreg
        path = path.replace("/", "\\")
        hives = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKCR": winreg.HKEY_CLASSES_ROOT,
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKU": winreg.HKEY_USERS,
            "HKEY_USERS": winreg.HKEY_USERS,
        }
        parts = path.split("\\", 1)
        hive = hives.get(parts[0].upper())
        subkey = parts[1] if len(parts) > 1 else ""
        return hive, subkey

    def _type_name(self, reg_type: int) -> str:
        import winreg
        names = {
            winreg.REG_SZ: "REG_SZ",
            winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
            winreg.REG_DWORD: "REG_DWORD",
            winreg.REG_QWORD: "REG_QWORD",
            winreg.REG_BINARY: "REG_BINARY",
            winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
        }
        return names.get(reg_type, f"TYPE_{reg_type}")


class RegistryWriteTool(BaseTool):
    name = "registry_write"
    description = "Write a value to a Windows registry key. Creates key if needed. USE WITH CAUTION."
    parameters = {"type": "object", "properties": {
        "key_path": {"type": "string"},
        "value_name": {"type": "string"},
        "value": {"type": "string"},
        "value_type": {"type": "string", "enum": ["REG_SZ", "REG_DWORD", "REG_EXPAND_SZ"], "default": "REG_SZ"},
    }, "required": ["key_path", "value_name", "value"]}

    # Blocked paths that could break the system
    BLOCKED_PATHS = [
        "HKLM\\SYSTEM\\CurrentControlSet",
        "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
        "HKLM\\SECURITY",
        "HKLM\\SAM",
    ]

    def run(self, key_path: str, value_name: str, value: str, value_type: str = "REG_SZ") -> str:
        # Safety check
        for blocked in self.BLOCKED_PATHS:
            if key_path.upper().startswith(blocked.upper()):
                return f"BLOCKED: Writing to {key_path} is not allowed (critical system path)."

        try:
            import winreg
            reader = RegistryReadTool()
            hive, subkey = reader._parse_key(key_path)
            if hive is None:
                return f"Invalid hive in: {key_path}"

            type_map = {
                "REG_SZ": winreg.REG_SZ,
                "REG_DWORD": winreg.REG_DWORD,
                "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
            }
            reg_type = type_map.get(value_type, winreg.REG_SZ)

            key = winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_WRITE)
            if reg_type == winreg.REG_DWORD:
                winreg.SetValueEx(key, value_name, 0, reg_type, int(value))
            else:
                winreg.SetValueEx(key, value_name, 0, reg_type, value)
            winreg.CloseKey(key)
            return f"Set {key_path}\\{value_name} = {value} ({value_type})"
        except PermissionError:
            return f"Access denied. Need admin privileges to write to {key_path}."
        except Exception as e:
            return f"Error: {e}"


class RegistrySearchTool(BaseTool):
    name = "registry_search"
    description = "Search registry for keys or values matching a pattern."
    parameters = {"type": "object", "properties": {
        "root_path": {"type": "string", "description": "Registry path to search under"},
        "search_term": {"type": "string", "description": "Text to search for in key/value names"},
        "max_results": {"type": "integer", "default": 20},
    }, "required": ["root_path", "search_term"]}

    def run(self, root_path: str, search_term: str, max_results: int = 20) -> str:
        try:
            import winreg
            reader = RegistryReadTool()
            hive, subkey = reader._parse_key(root_path)
            if hive is None:
                return f"Invalid hive: {root_path}"

            results = []
            self._search_recursive(hive, subkey, search_term.lower(), results, max_results, depth=0)

            if not results:
                return f"No matches for '{search_term}' under {root_path}"
            return f"Found {len(results)} matches:\n" + "\n".join(results)
        except Exception as e:
            return f"Error: {e}"

    def _search_recursive(self, hive, subkey, term, results, max_results, depth):
        import winreg
        if len(results) >= max_results or depth > 4:
            return
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
            # Check values
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if term in name.lower() or term in str(value).lower():
                        results.append(f"  {subkey}\\{name} = {str(value)[:80]}")
                    i += 1
                except OSError:
                    break
            # Recurse subkeys
            i = 0
            while True:
                try:
                    child = winreg.EnumKey(key, i)
                    if term in child.lower():
                        results.append(f"  {subkey}\\{child} (key)")
                    self._search_recursive(hive, f"{subkey}\\{child}", term, results, max_results, depth + 1)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except (PermissionError, OSError):
            pass

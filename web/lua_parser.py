"""
lua_parser.py — lupa-based reader and Lua serializer for bullets.lua

Usage:
    from lua_parser import read_bullets, read_proficiency_keys, lua_serialize
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COMPANY_ORDER = [
    "instapage", "nerdwallet", "stubhub",
    "aenetworks", "adweek", "prometheus", "mediabistro", None,
]

COMPANY_HEADERS = {
    None:          "PERSONAL / INDEPENDENT (nil company — no employer context)",
    "instapage":   "INSTAPAGE",
    "nerdwallet":  "NERDWALLET",
    "stubhub":     "STUBHUB",
    "aenetworks":  "A&E NETWORKS",
    "adweek":      "ADWEEK",
    "prometheus":  "PROMETHEUS",
    "mediabistro": "MEDIABISTRO",
}

FIELD_ORDER = [
    "proficiencies", "pmm_proficiencies",
    "experience_text", "proficiency_text",
    "pmm_experience_text", "pmm_proficiency_text",
    "alts",
]


# ─── Reader ──────────────────────────────────────────────────────────────────

def _lua_to_python(obj):
    """Recursively convert a lupa Lua object to a Python dict/list/scalar."""
    if obj is None:
        return None
    if not hasattr(obj, "items"):
        return obj
    items = list(obj.items())
    if not items:
        return {}
    keys = [k for k, _ in items]
    if all(isinstance(k, int) for k in keys):
        return [_lua_to_python(v) for _, v in sorted(items)]
    return {str(k): _lua_to_python(v) for k, v in items}


def read_bullets():
    """Execute bullets.lua via lupa and return as a Python list of dicts."""
    from lupa import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PROJECT_ROOT, "data", "bullets.lua")
    with open(path) as f:
        lua.execute(f.read())
    return _lua_to_python(lua.globals().bullets)


def read_proficiency_keys():
    """Return {'pm': [...], 'pmm': [...]} sorted key lists."""
    from lupa import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)

    with open(os.path.join(PROJECT_ROOT, "includes", "proficiencies.lua")) as f:
        lua.execute(f.read())
    pm_keys = sorted(str(k) for k in lua.globals().proficiencies.keys())

    with open(os.path.join(PROJECT_ROOT, "includes", "pmm", "proficiencies.lua")) as f:
        lua.execute(f.read())
    pmm_keys = sorted(str(k) for k in lua.globals().pmm_proficiencies.keys())

    return {"pm": pm_keys, "pmm": pmm_keys}


# ─── Serializer ──────────────────────────────────────────────────────────────

def _lua_str(s):
    """Escape a Python string for a Lua double-quoted string literal."""
    s = str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    return f'"{s}"'


def _serialize_bullet(bullet):
    lines = ["  {"]

    co = bullet.get("company")
    lines.append(f"    company = {'nil' if co is None else _lua_str(co)},")

    name = bullet.get("name")
    if name:
        lines.append(f"    name = {_lua_str(name)},")

    for field in ("proficiencies", "pmm_proficiencies"):
        val = bullet.get(field)
        if not val:
            continue
        items_str = ", ".join(_lua_str(s) for s in val)
        lines.append(f"    {field} = {{ {items_str} }},")

    for field in ("experience_text", "proficiency_text", "pmm_experience_text", "pmm_proficiency_text"):
        val = bullet.get(field)
        if not val:
            continue
        lines.append(f"    {field} = {_lua_str(val)},")

    alts = bullet.get("alts")
    if alts:
        lines.append("    alts = {")
        for alt in alts:
            lines.append(f"      {_lua_str(alt)},")
        lines.append("    },")

    cached = bullet.get("cached_idx")
    if cached:
        inner = ", ".join(f"{k} = {v}" for k, v in sorted(cached.items()))
        lines.append(f"    cached_idx = {{ {inner} }},")

    lines.append("  },")
    return "\n".join(lines)


def lua_serialize(bullets):
    """Serialize a list of bullet dicts to bullets.lua file content."""
    groups: dict = {}
    for b in bullets:
        co = b.get("company")
        groups.setdefault(co, []).append(b)

    known = set(COMPANY_ORDER)
    extra = [co for co in groups if co not in known]
    order = [co for co in COMPANY_ORDER if co in groups] + extra

    lines = [
        "-- Unified bullet store",
        "-- Single source of truth for all resume bullet content.",
        "-- Each record is a self-contained document with all variant phrasings embedded.",
        "--",
        "-- Fields:",
        "--   company          : key into companies table (nil = personal/independent)",
        "--   proficiencies    : array of skill keys — drives proficiency section",
        "--   experience_text  : canonical bullet for experience view (\"none\" = proficiency/archive-only)",
        "--   proficiency_text : optional reframe for proficiency view (falls back to experience_text if nil)",
        "--   alts             : alternate phrasings collected from archived resumes",
        "",
        "bullets = {",
    ]

    for co in order:
        header = COMPANY_HEADERS.get(co) or (str(co).upper() if co else "PERSONAL / INDEPENDENT")
        lines.append("")
        lines.append(f"  -- {'=' * 60}")
        lines.append(f"  -- {header}")
        lines.append(f"  -- {'=' * 60}")
        lines.append("")
        for b in groups[co]:
            lines.append(_serialize_bullet(b))
            lines.append("")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


# ─── Round-trip test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Reading bullets...")
    bullets = read_bullets()
    print(f"  {len(bullets)} bullets loaded")

    print("Reading proficiency keys...")
    keys = read_proficiency_keys()
    print(f"  PM keys:  {keys['pm']}")
    print(f"  PMM keys: {keys['pmm']}")

    print("Serializing back to Lua...")
    lua_out = lua_serialize(bullets)
    print(f"  {len(lua_out)} bytes")
    print("Round-trip OK.")

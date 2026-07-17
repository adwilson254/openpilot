"""Guard: no os.nice()/os.setpriority() at module import time in OpenRivian code.

The openpilot process manager PRE-IMPORTS every registered daemon module inside
the manager process (manager_init -> prepare -> importlib.import_module) BEFORE
forking any child. A module-level os.nice(19) therefore demotes the manager
itself, and -- because an unprivileged process can never lower its nice again --
EVERY subsequently forked openpilot process (camerad, pandad, modeld, locationd,
selfdrived, ui, ...) inherits nice 19. Nice-0 system tasks then preempt the
whole stack in bursts, consumers see message-arrival jitter, mid-tier daemons
stamp valid=False, and selfdrived raises commIssue noEntry/softDisable storms:
"TAKE CONTROL IMMEDIATELY / Communication Issue Between Processes" on engage.
(Root-caused 2026-07-16 from procLog.procs[].nice in the Fail At End rlog:
the whole stack ran at nice 19 on dev vs nice 0 on clean.)

Rule enforced: priority changes are only allowed INSIDE a function (e.g. main(),
which runs in the forked child) -- never at module scope. This is a static AST
check so it needs no imports of the daemons and works in any environment.
"""
import ast
from pathlib import Path

OPENRIVIAN_ROOT = Path(__file__).resolve().parents[1]

# tests/ contains this checker and string literals mentioning the pattern;
# dashboard/ is the JS app (no python expected, excluded for speed/noise).
EXCLUDE_DIRS = {"tests", "dashboard"}

PRIORITY_FUNC_NAMES = {"nice", "setpriority"}


def _priority_call_name(node):
    """Return the offending name if `node` is a call to *.nice / *.setpriority."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in PRIORITY_FUNC_NAMES:
        return func.attr
    if isinstance(func, ast.Name) and func.id in PRIORITY_FUNC_NAMES:
        return func.id
    return None


def module_scope_priority_calls(tree):
    """Return [(lineno, name)] for priority calls that execute at import time.

    Function/lambda BODIES are deferred (they run only when called), but their
    decorators and default-argument expressions DO execute at import time, so
    those are still scanned. Class bodies execute at import time and are scanned.
    """
    hits = []

    def visit(node, deferred):
        name = _priority_call_name(node)
        if name is not None and not deferred:
            hits.append((node.lineno, name))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                visit(dec, deferred)
            for default in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
                visit(default, deferred)
            for stmt in node.body:
                visit(stmt, True)
        elif isinstance(node, ast.Lambda):
            for default in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
                visit(default, deferred)
            visit(node.body, True)
        else:
            for child in ast.iter_child_nodes(node):
                visit(child, deferred)

    visit(tree, False)
    return hits


def test_no_module_level_priority_calls():
    py_files = [
        p for p in OPENRIVIAN_ROOT.rglob("*.py")
        if not any(part in EXCLUDE_DIRS for part in p.relative_to(OPENRIVIAN_ROOT).parts)
    ]
    assert py_files, f"no python files found under {OPENRIVIAN_ROOT}"

    offenders = []
    for path in sorted(py_files):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, name in module_scope_priority_calls(tree):
            offenders.append(f"{path.relative_to(OPENRIVIAN_ROOT)}:{lineno} calls {name}() at module scope")

    assert not offenders, (
        "os.nice()/os.setpriority() at module import time runs inside the process "
        "manager during its daemon pre-import and demotes the ENTIRE openpilot "
        "stack. Move the call inside main():\n  " + "\n  ".join(offenders)
    )


# --- self-tests for the detector itself -------------------------------------

def test_detector_catches_the_original_bug_pattern():
    bad = (
        "import os\n"
        "try:\n"
        "    os.nice(19)\n"
        "except Exception:\n"
        "    pass\n"
    )
    assert module_scope_priority_calls(ast.parse(bad)) == [(3, "nice")]


def test_detector_catches_setpriority_and_bare_nice():
    bad = "import os\nfrom os import nice\nos.setpriority(0, 0, 19)\nnice(19)\n"
    assert module_scope_priority_calls(ast.parse(bad)) == [(3, "setpriority"), (4, "nice")]


def test_detector_allows_nice_inside_main():
    good = (
        "import os\n"
        "def main():\n"
        "    try:\n"
        "        os.nice(19)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert module_scope_priority_calls(ast.parse(good)) == []

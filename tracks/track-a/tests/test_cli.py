"""tools/run_pipeline.py is a thin wrapper over track_a.api."""

import importlib.util
import json
from pathlib import Path

from ta_helpers import REAL_CASES

CLI = Path(__file__).resolve().parents[1] / "tools" / "run_pipeline.py"


def _cli():
    spec = importlib.util.spec_from_file_location("ta_run_pipeline", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_show_and_error(capsys, cases_root):
    cli = _cli()
    assert cli.main(["show", str(REAL_CASES / "micrometer")]) == 0
    assert json.loads(capsys.readouterr().out)["runtime_label"] == "SYNTHETIC"
    assert cli.main(["review", str(cases_root / "micrometer"), "approve", "--reviewer", "Jim"]) == 1
    assert json.loads(capsys.readouterr().err)["error"]["category"] == "INVALID_INPUT"

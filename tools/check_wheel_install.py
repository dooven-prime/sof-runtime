"""Build and exercise an installed wheel with its bundled contracts."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "automata" / "cerny4.json"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="sof-runtime-wheel-check-") as temporary:
        work = Path(temporary)
        wheel_dir = work / "dist"
        run(
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
        )
        environment_dir = work / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment_dir)
        scripts = environment_dir / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        wheel = next(wheel_dir.glob("*.whl"))
        run(str(python), "-m", "pip", "install", f"{wheel}[service]")

        workspace = work / "workspace"
        workspace.mkdir()
        service_root = workspace / "service"
        adopter_case = service_root / "adopter" / "case"
        shutil.copytree(ROOT / "examples" / "external-adapter-finite-state", adopter_case)
        shutil.copytree(ROOT / "profiles", workspace / "profiles")
        env = os.environ.copy()
        env["SOF_RUNTIME_WORKSPACE"] = str(workspace)
        run(
            str(python),
            "-c",
            (
                "from sof_runtime.action import validate_action; "
                "from sof_runtime.comparison import validate_audit; "
                "from sof_runtime.paths import (ACTION_CONTRACT_ROOT, "
                "COMPARISON_CONTRACT_ROOT, REPORTING_CONTRACT_ROOT, "
                "SERVICE_CONTRACT_ROOT); "
                "required=('sofrs.schema.json','assembly-profile.schema.json',"
                "'validation-receipt.schema.json'); "
                "assert all((REPORTING_CONTRACT_ROOT / name).is_file() "
                "for name in required); "
                "assert all((COMPARISON_CONTRACT_ROOT / name).is_file() for name in "
                "('sofaudit.schema.json','validation-receipt.schema.json',"
                "'coordinate-semantics-registry.json')); "
                "assert all((ACTION_CONTRACT_ROOT / name).is_file() for name in "
                "('sofaction.schema.json','validation-receipt.schema.json')); "
                "assert all((SERVICE_CONTRACT_ROOT / name).is_file() for name in "
                "('service-request.schema.json','service-response.schema.json',"
                "'service-error.schema.json','job.schema.json')); "
                "assert callable(validate_audit) and callable(validate_action)"
            ),
            env=env,
        )
        run(
            str(python),
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from sof_runtime.transports.http import create_app; "
                f"root=r'{service_root}'; "
                "client=TestClient(create_app(workspace_root=root)); "
                "payload={'contract_id':'sof-runtime.service-request.v1',"
                "'request_id':'wheel-http-1','workspace_id':'adopter',"
                "'operation':'realize','input':{'case_directory':'case',"
                "'run_directory':'run'}}; "
                "response=client.post('/v1/realizations',json=payload); "
                "assert response.status_code == 200, response.text; "
                "body=response.json(); "
                "assert body['status']=='succeeded'; "
                "assert body['result']['canonical_compilable'] is True; "
                "assert body['semantic_run_id'].startswith('semrun:sha256:'); "
                "assert len(body['artifacts']) == 5"
            ),
            env=env,
        )
        run(
            str(python),
            "-m",
            "sof_runtime.cli.main",
            "validate-sofaudit",
            "--help",
            env=env,
        )
        run(
            str(python),
            "-m",
            "sof_runtime.cli.main",
            "validate-source",
            str(SOURCE),
            env=env,
        )
        run_dir = workspace / "rank-run"
        run(
            str(python),
            "-m",
            "sof_runtime.cli.main",
            "run",
            "rank-collapse",
            str(SOURCE),
            "--run-dir",
            str(run_dir),
            env=env,
        )
        run(
            str(python),
            "-m",
            "sof_runtime.cli.main",
            "validate",
            str(run_dir / "run-response.json"),
            env=env,
        )
    print(
        "PASS: installed wheel carries compiler, runtime, reporting, comparison, "
        "action, and service contracts, exposes downstream validators, completes a "
        "validated run, and serves an HTTP realization from the installed wheel"
    )


if __name__ == "__main__":
    main()

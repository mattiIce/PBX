#!/usr/bin/env python3
"""Generate systemd service files with correct paths for this installation.

Usage:
    # Preview the generated service file
    python3 scripts/generate_service.py --dry-run

    # Generate and install (requires root)
    sudo python3 scripts/generate_service.py --install

    # Custom user/group
    sudo python3 scripts/generate_service.py --install --user pbx --group pbx
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


def detect_paths(
    venv_override: str | None = None,
) -> tuple[Path, Path, Path]:
    """Detect project root, venv path, and python binary.

    Returns (project_root, venv_path, python_bin).
    """
    project_root = Path(__file__).resolve().parent.parent

    # Allow explicit override
    if venv_override:
        venv_path = Path(venv_override).resolve()
        python_bin = venv_path / "bin" / "python3"
        if python_bin.exists():
            return project_root, venv_path, python_bin

    # Check common venv locations
    for venv_name in ("venv", ".venv"):
        venv_candidate = project_root / venv_name
        python_candidate = venv_candidate / "bin" / "python3"
        if python_candidate.exists():
            return project_root, venv_candidate, python_candidate

    # Check if the current interpreter is inside a venv under project_root
    current_prefix = Path(sys.prefix)
    if current_prefix != Path(sys.base_prefix):
        python_bin = current_prefix / "bin" / "python3"
        if python_bin.exists():
            return project_root, current_prefix, python_bin

    # Fall back to system python — venv_path still set to the conventional
    # location so the generated service has a reasonable default.
    python_bin = Path(shutil.which("python3") or "/usr/bin/python3")
    return project_root, project_root / "venv", python_bin


def generate_pbx_service(
    project_root: Path,
    venv_path: Path,
    python_bin: Path,
    user: str = "root",
    group: str = "root",
) -> str:
    """Return the systemd unit-file content for the PBX service."""
    protect_home = "false" if str(project_root).startswith(("/root", "/home")) else "true"
    pre_start = project_root / "scripts" / "pre-start.sh"

    return textwrap.dedent(f"""\
        [Unit]
        Description=Warden VoIP PBX System
        Documentation=https://github.com/mattiIce/PBX
        Wants=network-online.target
        After=network-online.target postgresql.service redis.service

        [Service]
        Type=simple
        User={user}
        Group={group}
        WorkingDirectory={project_root}
        EnvironmentFile=-{project_root}/.env
        Environment="PATH={venv_path}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        SyslogIdentifier=pbx
        ExecStartPre=/bin/bash {pre_start}
        ExecStart={python_bin} {project_root}/main.py
        Restart=on-failure
        RestartSec=5
        # Allow 35s for the PBX graceful shutdown (30s internal timeout + 5s margin)
        TimeoutStopSec=35
        KillSignal=SIGINT
        StandardOutput=journal
        StandardError=journal

        # Security hardening
        NoNewPrivileges=true
        PrivateTmp=true
        ProtectSystem=full
        ProtectHome={protect_home}
        ReadWritePaths={project_root}

        # Resource limits
        LimitNOFILE=65536
        LimitNPROC=4096

        [Install]
        WantedBy=multi-user.target
    """)


def generate_startup_tests_service(
    project_root: Path,
    user: str = "root",
    group: str = "root",
) -> str:
    """Return the systemd unit-file content for the startup-tests service."""
    return textwrap.dedent(f"""\
        [Unit]
        Description=Warden VoIP System Startup Tests
        After=network.target pbx.service

        [Service]
        Type=oneshot
        User={user}
        Group={group}
        WorkingDirectory={project_root}
        ExecStart={project_root}/run_startup_tests.sh
        StandardOutput=journal
        StandardError=journal
        SuccessExitStatus=0 1

        [Install]
        WantedBy=multi-user.target
    """)


def install_service(path: Path, content: str) -> None:
    """Write a service file to /etc/systemd/system/ and daemon-reload."""
    # path.stem strips the .generated suffix (e.g. "pbx.service.generated" -> "pbx.service")
    dest = Path("/etc/systemd/system") / path.stem
    dest.write_text(content, encoding="utf-8")
    print(f"  Installed {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate systemd service files with correct paths.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install to /etc/systemd/system/ and run systemctl daemon-reload",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated service file without writing",
    )
    parser.add_argument("--user", default="root", help="Service User (default: root)")
    parser.add_argument("--group", default="root", help="Service Group (default: root)")
    parser.add_argument("--venv", default=None, help="Override venv path")
    args = parser.parse_args()

    project_root, venv_path, python_bin = detect_paths(args.venv)

    pbx_content = generate_pbx_service(
        project_root,
        venv_path,
        python_bin,
        args.user,
        args.group,
    )
    tests_content = generate_startup_tests_service(
        project_root,
        args.user,
        args.group,
    )

    if args.dry_run:
        print("# --- pbx.service ---")
        print(pbx_content)
        print("# --- pbx-startup-tests.service ---")
        print(tests_content)
        return

    # Write local copies
    pbx_service = project_root / "pbx.service.generated"
    pbx_service.write_text(pbx_content, encoding="utf-8")
    print(f"Generated {pbx_service}")

    tests_service = project_root / "pbx-startup-tests.service.generated"
    tests_service.write_text(tests_content, encoding="utf-8")
    print(f"Generated {tests_service}")

    if args.install:
        if os.geteuid() != 0:
            print("ERROR: --install requires root privileges", file=sys.stderr)
            sys.exit(1)

        install_service(pbx_service, pbx_content)
        install_service(tests_service, tests_content)

        subprocess.run(["systemctl", "daemon-reload"], check=False)
        print("  systemctl daemon-reload complete")

        subprocess.run(["systemctl", "enable", "pbx.service"], check=False)
        print("  pbx.service enabled (will start on boot)")

        print("\nStart the service with: sudo systemctl start pbx")
        print("View logs with:         sudo journalctl -u pbx -f")


if __name__ == "__main__":
    main()

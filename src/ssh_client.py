"""SSH client for remote compute target operations."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import paramiko

from .models import ComputeTarget


class SSHClient:
    """SSH client wrapper for remote operations."""

    def __init__(self, target: ComputeTarget):
        self.target = target
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self) -> None:
        """Establish SSH connection to the target."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.target.ssh_host,
            "port": self.target.ssh_port,
            "username": self.target.ssh_user,
        }

        if self.target.auth_type == "key":
            key_path = os.path.expanduser(self.target.ssh_key_path or "~/.ssh/id_rsa")
            connect_kwargs["key_filename"] = key_path
        else:
            connect_kwargs["password"] = self.target.ssh_password

        self._client.connect(**connect_kwargs)
        self._sftp = self._client.open_sftp()

    def close(self) -> None:
        """Close SSH and SFTP connections."""
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def run_command(self, cmd: str, timeout: int = 300) -> tuple[int, str, str]:
        """Execute a command on the remote server.

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self._client:
            raise RuntimeError("SSH client not connected")

        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, stdout.read().decode("utf-8"), stderr.read().decode("utf-8")

    def mkdir_p(self, remote_path: str) -> None:
        """Create remote directory and parents if they don't exist."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        remote_path = self._expand_remote_path(remote_path)
        parts = remote_path.split("/")
        current = ""

        for part in parts:
            if not part:
                current = "/"
                continue
            current = f"{current}/{part}" if current != "/" else f"/{part}"
            try:
                self._sftp.stat(current)
            except FileNotFoundError:
                self._sftp.mkdir(current)

    def upload_file(self, local_path: str | Path, remote_path: str) -> None:
        """Upload a single file to the remote server."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        local_path = Path(local_path)
        remote_path = self._expand_remote_path(remote_path)

        remote_dir = str(Path(remote_path).parent)
        self.mkdir_p(remote_dir)

        self._sftp.put(str(local_path), remote_path)

    def upload_directory(self, local_dir: str | Path, remote_dir: str) -> None:
        """Recursively upload a local directory to the remote server."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        local_dir = Path(local_dir)
        remote_dir = self._expand_remote_path(remote_dir)

        self.mkdir_p(remote_dir)

        for item in local_dir.rglob("*"):
            if item.name.startswith(".") or "__pycache__" in str(item):
                continue

            relative = item.relative_to(local_dir)
            remote_path = f"{remote_dir}/{relative}"

            if item.is_dir():
                self.mkdir_p(remote_path)
            else:
                self.upload_file(item, remote_path)

    def download_file(self, remote_path: str, local_path: str | Path) -> None:
        """Download a single file from the remote server."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        local_path = Path(local_path)
        remote_path = self._expand_remote_path(remote_path)

        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._sftp.get(remote_path, str(local_path))

    def download_directory(self, remote_dir: str, local_dir: str | Path) -> None:
        """Recursively download a remote directory to local."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        local_dir = Path(local_dir)
        remote_dir = self._expand_remote_path(remote_dir)

        local_dir.mkdir(parents=True, exist_ok=True)

        self._download_dir_recursive(remote_dir, local_dir)

    def _download_dir_recursive(self, remote_dir: str, local_dir: Path) -> None:
        """Recursively download directory contents."""
        if not self._sftp:
            return

        for entry in self._sftp.listdir_attr(remote_dir):
            remote_path = f"{remote_dir}/{entry.filename}"
            local_path = local_dir / entry.filename

            if stat.S_ISDIR(entry.st_mode or 0):
                local_path.mkdir(exist_ok=True)
                self._download_dir_recursive(remote_path, local_path)
            else:
                self._sftp.get(remote_path, str(local_path))

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote server."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        remote_path = self._expand_remote_path(remote_path)
        try:
            self._sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def read_file(self, remote_path: str) -> str:
        """Read a text file from the remote server."""
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")

        remote_path = self._expand_remote_path(remote_path)
        with self._sftp.open(remote_path, "r") as f:
            return f.read().decode("utf-8")

    def _expand_remote_path(self, path: str) -> str:
        """Expand ~ in remote path to actual home directory."""
        if path.startswith("~/"):
            exit_code, stdout, _ = self.run_command("echo $HOME")
            if exit_code == 0:
                home = stdout.strip()
                return path.replace("~", home, 1)
        return path


def test_connection(target: ComputeTarget) -> tuple[bool, str, str | None]:
    """Test SSH connection and check Python availability.

    Returns:
        Tuple of (success, message, python_version)
    """
    try:
        with SSHClient(target) as client:
            exit_code, stdout, stderr = client.run_command("python3 --version")
            if exit_code != 0:
                return False, f"Python not found: {stderr}", None
            python_version = stdout.strip()
            return True, "Connection successful", python_version
    except paramiko.AuthenticationException:
        return False, "Authentication failed", None
    except paramiko.SSHException as e:
        return False, f"SSH error: {e}", None
    except Exception as e:
        return False, f"Connection failed: {e}", None


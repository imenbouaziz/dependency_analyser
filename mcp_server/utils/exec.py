"""
exec.py
Utilities for executing external commands and Git operations.
"""

from __future__ import annotations
import subprocess
import tempfile
import shutil
import os
from typing import Dict, List, Optional


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: int = 300,
    capture_output: bool = True
) -> Dict:
    """
    Execute a shell command and return the result.
    
    Args:
        cmd: Command and arguments as a list (e.g., ["mvn", "dependency:tree"])
        cwd: Working directory to execute the command in
        timeout: Maximum execution time in seconds (default 5 minutes)
        capture_output: Whether to capture stdout/stderr
    
    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "returncode": int,
            "error": str (if any)
        }
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=False
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command not found: {cmd[0]}"
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e)
        }


def run_git_clone(repo_url: str, dest_dir: str) -> Dict:
    """
    Clone a Git repository.
    
    Args:
        repo_url: Git repository URL (e.g., https://github.com/user/repo)
        dest_dir: Destination directory for the clone
    
    Returns:
        {
            "success": bool,
            "path": str (absolute path to cloned repo),
            "error": str (if any)
        }
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(dest_dir) if os.path.dirname(dest_dir) else ".", exist_ok=True)
    
    result = run_command(["git", "clone", repo_url, dest_dir], timeout=600)
    
    if result["success"]:
        return {
            "success": True,
            "path": os.path.abspath(dest_dir)
        }
    else:
        return {
            "success": False,
            "path": "",
            "error": result.get("error") or result.get("stderr") or "Git clone failed"
        }


def is_git_repo(path: str) -> bool:
    """
    Check if a directory is a Git repository.
    
    Args:
        path: Directory path to check
    
    Returns:
        True if path is a git repository, False otherwise
    """
    if not os.path.isdir(path):
        return False
    
    git_dir = os.path.join(path, ".git")
    return os.path.isdir(git_dir)


def clone_to_temp(repo_url: str) -> Dict:
    """
    Clone a Git repository to a temporary directory.
    
    Args:
        repo_url: Git repository URL
    
    Returns:
        {
            "success": bool,
            "path": str (path to temp clone),
            "error": str (if any)
        }
    """
    temp_dir = tempfile.mkdtemp(prefix="dep_analyzer_")
    
    # Extract repo name from URL for better directory naming
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    clone_path = os.path.join(temp_dir, repo_name)
    
    return run_git_clone(repo_url, clone_path)

#!/usr/bin/env python3
"""
Comprehensive verification script for checking all expected .wav files
in the PBX repository after running verify_and_commit_voice_files.sh
"""

import os
import sys
from pathlib import Path
import subprocess
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Expected voice files
AUTO_ATTENDANT_FILES = [
    'welcome.wav',
    'main_menu.wav',
    'invalid.wav',
    'timeout.wav',
    'transferring.wav',
]

VOICEMAIL_PROMPT_FILES = [
    'enter_pin.wav',
    'invalid_pin.wav',
    'main_menu.wav',
    'message_menu.wav',
    'no_messages.wav',
    'you_have_messages.wav',
    'goodbye.wav',
    'leave_message.wav',
    'recording_greeting.wav',
    'greeting_saved.wav',
    'message_deleted.wav',
    'end_of_messages.wav',
]


def get_repo_root() -> Path:
    """Get the repository root directory."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Fallback: assume script is in scripts/ directory
        return Path(__file__).parent.parent


def check_file_exists(filepath: Path) -> Tuple[bool, int]:
    """Check if file exists and return its size."""
    if filepath.exists() and filepath.is_file():
        return True, filepath.stat().st_size
    return False, 0


def check_git_tracked(filepath: Path, repo_root: Path) -> bool:
    """Check if file is tracked in git."""
    try:
        rel_path = filepath.relative_to(repo_root)
        result = subprocess.run(
            ['git', 'ls-files', '--', str(rel_path)],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=True
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return False


def verify_wav_format(filepath: Path) -> Dict[str, str]:
    """Verify WAV file format using 'file' command."""
    if not filepath.exists():
        return {'error': 'File does not exist'}
    
    try:
        result = subprocess.run(
            ['file', str(filepath)],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        
        # Parse the output
        info = {
            'format': 'Unknown',
            'sample_rate': 'Unknown',
            'bit_depth': 'Unknown',
            'channels': 'Unknown',
        }
        
        if 'WAVE' in output or 'WAV' in output:
            info['format'] = 'WAV'
        
        if '8000 Hz' in output:
            info['sample_rate'] = '8000 Hz'
        elif '16000 Hz' in output:
            info['sample_rate'] = '16000 Hz'
        elif '44100 Hz' in output:
            info['sample_rate'] = '44100 Hz'
        
        if '16 bit' in output:
            info['bit_depth'] = '16-bit'
        elif '8 bit' in output:
            info['bit_depth'] = '8-bit'
        
        if 'mono' in output.lower():
            info['channels'] = 'mono'
        elif 'stereo' in output.lower():
            info['channels'] = 'stereo'
        
        return info
    except subprocess.CalledProcessError:
        return {'error': 'Could not determine format'}


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_section(text: str):
    """Print a section header."""
    print(f"\n{BOLD}{text}{RESET}")
    print(f"{'-' * len(text)}")


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    """Main verification function."""
    repo_root = get_repo_root()
    aa_dir = repo_root / 'auto_attendant'
    vm_dir = repo_root / 'voicemail_prompts'
    
    print_header("WAV FILE VERIFICATION REPORT")
    
    print(f"Repository Root: {repo_root}")
    print(f"Auto Attendant Dir: {aa_dir}")
    print(f"Voicemail Prompts Dir: {vm_dir}")
    
    # Statistics
    total_expected = len(AUTO_ATTENDANT_FILES) + len(VOICEMAIL_PROMPT_FILES)
    aa_found = 0
    vm_found = 0
    aa_tracked = 0
    vm_tracked = 0
    total_size = 0
    
    # Check Auto Attendant files
    print_section(f"Auto Attendant Files ({len(AUTO_ATTENDANT_FILES)} expected)")
    
    for filename in AUTO_ATTENDANT_FILES:
        filepath = aa_dir / filename
        exists, size = check_file_exists(filepath)
        tracked = check_git_tracked(filepath, repo_root) if exists else False
        
        if exists:
            aa_found += 1
            total_size += size
            status_icon = f"{GREEN}✓{RESET}"
            size_str = format_size(size)
            
            if tracked:
                aa_tracked += 1
                git_status = f"{GREEN}[tracked]{RESET}"
            else:
                git_status = f"{YELLOW}[not tracked]{RESET}"
            
            print(f"  {status_icon} {filename:25s} {size_str:>10s} {git_status}")
        else:
            status_icon = f"{RED}✗{RESET}"
            print(f"  {status_icon} {filename:25s} {RED}MISSING{RESET}")
    
    # Check Voicemail Prompt files
    print_section(f"Voicemail Prompt Files ({len(VOICEMAIL_PROMPT_FILES)} expected)")
    
    for filename in VOICEMAIL_PROMPT_FILES:
        filepath = vm_dir / filename
        exists, size = check_file_exists(filepath)
        tracked = check_git_tracked(filepath, repo_root) if exists else False
        
        if exists:
            vm_found += 1
            total_size += size
            status_icon = f"{GREEN}✓{RESET}"
            size_str = format_size(size)
            
            if tracked:
                vm_tracked += 1
                git_status = f"{GREEN}[tracked]{RESET}"
            else:
                git_status = f"{YELLOW}[not tracked]{RESET}"
            
            print(f"  {status_icon} {filename:25s} {size_str:>10s} {git_status}")
        else:
            status_icon = f"{RED}✗{RESET}"
            print(f"  {status_icon} {filename:25s} {RED}MISSING{RESET}")
    
    # Summary
    total_found = aa_found + vm_found
    total_tracked = aa_tracked + vm_tracked
    
    print_section("Summary")
    print(f"  Total Expected:  {total_expected} files")
    print(f"  Files Found:     {total_found} files ({GREEN if total_found == total_expected else RED}{total_found}/{total_expected}{RESET})")
    print(f"    - Auto Attendant:    {aa_found}/{len(AUTO_ATTENDANT_FILES)}")
    print(f"    - Voicemail Prompts: {vm_found}/{len(VOICEMAIL_PROMPT_FILES)}")
    print(f"  Git Tracked:     {total_tracked} files ({GREEN if total_tracked > 0 else YELLOW}{total_tracked}/{total_found if total_found > 0 else total_expected}{RESET})")
    print(f"  Total Size:      {format_size(total_size)}")
    
    # Check if any files are found
    if total_found == 0:
        print_section("Status")
        print(f"{RED}⚠ NO WAV FILES FOUND{RESET}")
        print(f"\nThe wav files have not been generated yet.")
        print(f"\nTo generate them, run:")
        print(f"  {BLUE}cd {repo_root}{RESET}")
        print(f"  {BLUE}bash scripts/verify_and_commit_voice_files.sh{RESET}")
        print(f"\nOr generate manually with:")
        print(f"  {BLUE}python3 scripts/generate_tts_prompts.py --company 'Your Company'{RESET}")
        return 1
    
    elif total_found < total_expected:
        print_section("Status")
        print(f"{YELLOW}⚠ INCOMPLETE - Some files are missing{RESET}")
        print(f"\nMissing {total_expected - total_found} files.")
        print(f"\nTo generate missing files, run:")
        print(f"  {BLUE}bash scripts/verify_and_commit_voice_files.sh{RESET}")
        return 1
    
    else:
        print_section("Status")
        print(f"{GREEN}✓ ALL FILES PRESENT{RESET}")
        
        if total_tracked == 0:
            print(f"\n{YELLOW}Note: Files exist locally but are NOT tracked in git.{RESET}")
            print(f"They are excluded by .gitignore.")
            print(f"\nTo commit them to git, run:")
            print(f"  {BLUE}bash scripts/verify_and_commit_voice_files.sh{RESET}")
            print(f"\nOr manually:")
            print(f"  {BLUE}git add -f auto_attendant/*.wav voicemail_prompts/*.wav{RESET}")
            print(f"  {BLUE}git commit -m 'Add voice files'{RESET}")
        
        elif total_tracked == total_found:
            print(f"\n{GREEN}✓ All files are tracked in git.{RESET}")
        
        else:
            print(f"\n{YELLOW}Note: {total_found - total_tracked} files are not tracked in git.{RESET}")
    
    # Sample format verification
    if total_found > 0:
        print_section("Sample File Format Check")
        sample_file = None
        
        if aa_found > 0:
            sample_file = aa_dir / AUTO_ATTENDANT_FILES[0]
        elif vm_found > 0:
            sample_file = vm_dir / VOICEMAIL_PROMPT_FILES[0]
        
        if sample_file:
            format_info = verify_wav_format(sample_file)
            print(f"  Sample File: {sample_file.name}")
            
            if 'error' in format_info:
                print(f"  {RED}Error: {format_info['error']}{RESET}")
            else:
                print(f"    Format:      {format_info['format']}")
                print(f"    Sample Rate: {format_info['sample_rate']} {GREEN if format_info['sample_rate'] == '8000 Hz' else YELLOW}(expected: 8000 Hz){RESET}")
                print(f"    Bit Depth:   {format_info['bit_depth']} {GREEN if format_info['bit_depth'] == '16-bit' else YELLOW}(expected: 16-bit){RESET}")
                print(f"    Channels:    {format_info['channels']} {GREEN if format_info['channels'] == 'mono' else YELLOW}(expected: mono){RESET}")
    
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}\n")
    
    return 0 if total_found == total_expected else 1


if __name__ == '__main__':
    sys.exit(main())

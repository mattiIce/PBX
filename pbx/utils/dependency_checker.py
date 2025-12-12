"""
Dependency Checker for PBX System
Verifies that all required and optional dependencies are installed at startup
Reads dependencies from requirements.txt
"""
import importlib
import os
import re
import sys
from typing import Dict, List, Tuple


# Map package names to module names (when they differ)
PACKAGE_TO_MODULE = {
    'PyYAML': 'yaml',
    'psycopg2-binary': 'psycopg2',
}

# Features enabled by optional dependencies
OPTIONAL_FEATURES = {
    'psycopg2-binary': 'PostgreSQL database backend',
    'psycopg2': 'PostgreSQL database backend',
    'msal': 'Microsoft Teams/Outlook integration',
    'fido2': 'FIDO2/WebAuthn authentication',
    'opuslib': 'Opus codec support',
    'vosk': 'Voicemail transcription (offline)',
}

# Core dependencies (required for basic PBX operation)
CORE_PACKAGES = {'PyYAML', 'cryptography'}


def parse_requirements_txt(requirements_path: str = 'requirements.txt') -> Dict[str, str]:
    """
    Parse requirements.txt file
    
    Returns:
        Dictionary mapping package names to version specs (without comments)
    """
    requirements = {}
    
    if not os.path.exists(requirements_path):
        return requirements
    
    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
            
            # Parse package name and version spec
            # Matches: package>=1.0.0, package==1.0, package, etc.
            match = re.match(r'^([a-zA-Z0-9_-]+)([>=<!=]+.*)?', line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2) or ''
                requirements[package_name] = package_name + version_spec
    
    return requirements


def get_module_name(package_name: str) -> str:
    """Convert package name to module name"""
    return PACKAGE_TO_MODULE.get(package_name, package_name.lower().replace('-', '_'))


def check_module(module_name: str) -> bool:
    """Check if a Python module is installed"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def check_dependencies(verbose: bool = False, requirements_path: str = 'requirements.txt') -> Tuple[bool, Dict[str, List]]:
    """
    Check all dependencies from requirements.txt
    
    Args:
        verbose: If True, print detailed information
        requirements_path: Path to requirements.txt file
        
    Returns:
        Tuple of (all_core_ok, report_dict)
        - all_core_ok: True if all core dependencies are satisfied
        - report_dict: Dictionary with 'missing_core', 'missing_optional', 'available_optional'
    """
    missing_core = []
    missing_optional = []
    available_optional = []
    
    # Parse requirements.txt
    requirements = parse_requirements_txt(requirements_path)
    
    if not requirements:
        if verbose:
            print(f"  ⚠ Warning: No requirements found in {requirements_path}")
        return True, {
            'missing_core': [],
            'missing_optional': [],
            'available_optional': [],
        }
    
    # Check each requirement
    for package_name, package_spec in requirements.items():
        module_name = get_module_name(package_name)
        is_core = package_name in CORE_PACKAGES
        
        if not check_module(module_name):
            # Package is missing
            if is_core:
                missing_core.append(package_spec)
                if verbose:
                    print(f"  ✗ Missing CORE: {package_spec}")
            else:
                feature = OPTIONAL_FEATURES.get(package_name, 'Additional features')
                missing_optional.append({
                    'package': package_spec,
                    'feature': feature,
                })
                if verbose:
                    print(f"  ⚠ Missing optional: {package_spec} - enables {feature}")
        else:
            # Package is available
            if verbose:
                if is_core:
                    print(f"  ✓ Core: {package_name}")
                else:
                    feature = OPTIONAL_FEATURES.get(package_name, 'Additional features')
                    available_optional.append({
                        'package': package_spec,
                        'feature': feature,
                    })
                    print(f"  ✓ Optional: {package_name} - {feature}")
    
    report = {
        'missing_core': missing_core,
        'missing_optional': missing_optional,
        'available_optional': available_optional,
    }
    
    return len(missing_core) == 0, report


def print_dependency_report(report: Dict[str, List], verbose: bool = False) -> None:
    """Print a formatted dependency report"""
    missing_core = report['missing_core']
    missing_optional = report['missing_optional']
    available_optional = report['available_optional']
    
    # Core dependencies
    if missing_core:
        print("\n✗ MISSING REQUIRED DEPENDENCIES:")
        for package in missing_core:
            print(f"  - {package}")
        print("\nInstall missing dependencies with:")
        print(f"  pip install {' '.join(missing_core)}")
    else:
        print("✓ All core dependencies satisfied")
    
    # Optional dependencies - only show details in verbose mode
    if missing_optional:
        if verbose:
            print("\n⚠ MISSING OPTIONAL DEPENDENCIES:")
            for dep in missing_optional:
                print(f"  - {dep['package']}")
                print(f"    Feature: {dep['feature']}")
            print("\nTo enable these features, install:")
            packages = ' '.join([dep['package'] for dep in missing_optional])
            print(f"  pip install {packages}")
        else:
            # Concise output - just count
            count = len(missing_optional)
            print(f"⚠ {count} optional dependencies missing (use --verbose to see details)")
    else:
        if verbose:
            print("\n✓ All optional dependencies installed")
    
    # Show available optional features - only in verbose mode
    if available_optional and verbose:
        print("\n✓ ENABLED OPTIONAL FEATURES:")
        for dep in available_optional:
            print(f"  - {dep['feature']}")


def check_and_report(verbose: bool = False, strict: bool = True, requirements_path: str = 'requirements.txt') -> bool:
    """
    Check dependencies and print report
    
    Args:
        verbose: Show detailed information including optional dependencies
        strict: If True, fail if core dependencies are missing
        requirements_path: Path to requirements.txt file
        
    Returns:
        True if all required dependencies are satisfied (or strict=False)
    """
    all_core_ok, report = check_dependencies(verbose=False, requirements_path=requirements_path)
    
    print_dependency_report(report, verbose=verbose)
    
    if not all_core_ok and strict:
        print("\n✗ Cannot start: Missing required dependencies")
        return False
    
    return True


if __name__ == "__main__":
    # Run dependency check with verbose output
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    strict = '--strict' not in sys.argv or '-s' not in sys.argv
    
    success = check_and_report(verbose=True, strict=strict)
    sys.exit(0 if success else 1)

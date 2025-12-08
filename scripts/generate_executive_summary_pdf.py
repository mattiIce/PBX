#!/usr/bin/env python3
"""
Script to generate PDF version of the Executive Summary from Markdown.

This script converts EXECUTIVE_SUMMARY.md to EXECUTIVE_SUMMARY.pdf using pandoc.
The PDF includes proper formatting, table of contents, and styling.

Usage:
    python3 scripts/generate_executive_summary_pdf.py
"""

import subprocess
import sys
import os
from pathlib import Path


def generate_pdf():
    """Generate PDF from Executive Summary markdown file."""
    
    # Get the repository root directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Define input and output paths
    input_file = repo_root / "EXECUTIVE_SUMMARY.md"
    output_file = repo_root / "EXECUTIVE_SUMMARY.pdf"
    
    # Verify input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    print(f"Converting {input_file.name} to PDF...")
    
    # Pandoc command with options for better PDF output
    # Using wkhtmltopdf as the PDF engine to better handle Unicode/emoji characters
    pandoc_cmd = [
        "pandoc",
        str(input_file),
        "-o", str(output_file),
        "--pdf-engine=wkhtmltopdf",
        "--toc",  # Include table of contents
        "--toc-depth=3",  # Show up to 3 levels in TOC
        "-V", "margin-left=1in",  # Set margins
        "-V", "margin-right=1in",
        "-V", "margin-top=1in",
        "-V", "margin-bottom=1in",
        "--metadata", "title=Executive Summary: Aluminum Blanking PBX System",
        "--metadata", "author=Aluminum Blanking",
        "--metadata", "date=December 8, 2025",
    ]
    
    try:
        # Run pandoc
        result = subprocess.run(
            pandoc_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✅ PDF generated successfully: {output_file}")
        print(f"   File size: {output_file.stat().st_size / 1024:.2f} KB")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating PDF:")
        print(f"   Command: {' '.join(pandoc_cmd)}")
        print(f"   Return code: {e.returncode}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return 1
    except FileNotFoundError:
        print("❌ Error: pandoc or wkhtmltopdf not found. Please install:")
        print("   Ubuntu/Debian: sudo apt-get install pandoc wkhtmltopdf")
        print("   macOS: brew install pandoc && brew install --cask wkhtmltopdf")
        return 1


def main():
    """Main entry point."""
    print("=" * 70)
    print("Executive Summary PDF Generator")
    print("=" * 70)
    
    exit_code = generate_pdf()
    
    print("=" * 70)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

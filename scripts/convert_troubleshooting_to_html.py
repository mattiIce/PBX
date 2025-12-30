#!/usr/bin/env python3
"""
Convert TROUBLESHOOTING.md to a Windows-compatible HTML file.

This script converts the markdown troubleshooting guide to a standalone HTML file
that can be opened and read easily on Windows systems.
"""

import re
from pathlib import Path


def create_anchor_id(text):
    """Create URL-safe anchor ID from header text."""
    # Remove HTML tags and special characters
    text = re.sub(r'<[^>]+>', '', text)
    # Convert to lowercase and replace spaces with hyphens
    anchor = text.lower().strip()
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    anchor = re.sub(r'[-\s]+', '-', anchor)
    return anchor


def markdown_to_html(markdown_content):
    """
    Convert markdown content to HTML with proper formatting.
    
    Args:
        markdown_content: String containing markdown text
        
    Returns:
        String containing HTML content
    """
    html = markdown_content
    
    # Convert headers with anchor IDs
    def replace_h1(match):
        text = match.group(1)
        anchor_id = create_anchor_id(text)
        return f'<h1 id="{anchor_id}">{text}</h1>'
    
    def replace_h2(match):
        text = match.group(1)
        anchor_id = create_anchor_id(text)
        return f'<h2 id="{anchor_id}">{text}</h2>'
    
    def replace_h3(match):
        text = match.group(1)
        anchor_id = create_anchor_id(text)
        return f'<h3 id="{anchor_id}">{text}</h3>'
    
    def replace_h4(match):
        text = match.group(1)
        anchor_id = create_anchor_id(text)
        return f'<h4 id="{anchor_id}">{text}</h4>'
    
    html = re.sub(r'^# (.+)$', replace_h1, html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', replace_h2, html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', replace_h3, html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', replace_h4, html, flags=re.MULTILINE)
    
    # Convert bold text
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Convert italic text
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Convert inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Convert code blocks
    def replace_code_block(match):
        lang = match.group(1) if match.group(1) else ''
        code = match.group(2)
        # Escape HTML in code blocks
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre class="code-block {lang}"><code>{code}</code></pre>'
    
    html = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
    
    # Convert links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Convert horizontal rules
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    
    # Convert tables
    lines = html.split('\n')
    in_table = False
    table_lines = []
    result_lines = []
    
    for i, line in enumerate(lines):
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
        else:
            if in_table:
                result_lines.append(convert_table(table_lines))
                table_lines = []
                in_table = False
            result_lines.append(line)
    
    if in_table and table_lines:
        result_lines.append(convert_table(table_lines))
    
    html = '\n'.join(result_lines)
    
    # Convert lists
    html = convert_lists(html)
    
    # Convert paragraphs (lines that aren't already in HTML tags)
    lines = html.split('\n')
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.startswith('|'):
            result_lines.append(f'<p>{line}</p>')
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def convert_table(table_lines):
    """Convert markdown table to HTML table."""
    if len(table_lines) < 2:
        return '\n'.join(table_lines)
    
    html = ['<table class="info-table">']
    
    # Header row
    header = table_lines[0]
    cells = [cell.strip() for cell in header.split('|')[1:-1]]
    html.append('<thead><tr>')
    for cell in cells:
        html.append(f'<th>{cell}</th>')
    html.append('</tr></thead>')
    
    # Data rows (skip separator line)
    html.append('<tbody>')
    for row in table_lines[2:]:
        cells = [cell.strip() for cell in row.split('|')[1:-1]]
        html.append('<tr>')
        for cell in cells:
            html.append(f'<td>{cell}</td>')
        html.append('</tr>')
    html.append('</tbody>')
    
    html.append('</table>')
    return '\n'.join(html)


def convert_lists(text):
    """Convert markdown lists to HTML lists."""
    lines = text.split('\n')
    result = []
    in_ul = False
    in_ol = False
    
    for line in lines:
        stripped = line.strip()
        
        # Unordered list
        if re.match(r'^[-*+] ', stripped):
            if not in_ul:
                result.append('<ul>')
                in_ul = True
            content = re.sub(r'^[-*+] ', '', stripped)
            result.append(f'<li>{content}</li>')
        # Ordered list
        elif re.match(r'^\d+\. ', stripped):
            if not in_ol:
                result.append('<ol>')
                in_ol = True
            content = re.sub(r'^\d+\. ', '', stripped)
            result.append(f'<li>{content}</li>')
        else:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False
            result.append(line)
    
    # Close any open lists
    if in_ul:
        result.append('</ul>')
    if in_ol:
        result.append('</ol>')
    
    return '\n'.join(result)


def create_html_template(content, title="PBX System - Troubleshooting Guide"):
    """
    Create a complete HTML document with styling.
    
    Args:
        content: HTML body content
        title: Page title
        
    Returns:
        Complete HTML document as string
    """
    css = """
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }
        
        h2 {
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            margin-top: 30px;
        }
        
        h3 {
            color: #555;
            margin-top: 25px;
        }
        
        h4 {
            color: #666;
            margin-top: 20px;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            color: #e74c3c;
        }
        
        pre {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }
        
        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: 0.95em;
        }
        
        .code-block.bash code,
        .code-block.sh code {
            color: #2ecc71;
        }
        
        .code-block.yaml code,
        .code-block.yml code {
            color: #f39c12;
        }
        
        .code-block.python code {
            color: #3498db;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        table.info-table {
            background-color: white;
        }
        
        th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 10px 12px;
            border: 1px solid #ddd;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f0f0f0;
        }
        
        a {
            color: #3498db;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
            color: #2980b9;
        }
        
        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }
        
        ul, ol {
            margin: 10px 0;
            padding-left: 30px;
        }
        
        li {
            margin: 5px 0;
        }
        
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        p {
            margin: 10px 0;
        }
        
        .toc {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc li {
            margin: 8px 0;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .status-fixed {
            background-color: #2ecc71;
            color: white;
        }
        
        .status-documented {
            background-color: #3498db;
            color: white;
        }
        
        @media print {
            body {
                background-color: white;
            }
            
            .container {
                box-shadow: none;
            }
            
            pre {
                background-color: #f4f4f4;
                color: #333;
                border: 1px solid #ddd;
            }
        }
        
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .container {
                padding: 20px;
            }
            
            table {
                font-size: 0.9em;
            }
        }
    """
    
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="container">
{content}
    </div>
</body>
</html>
"""
    
    return template


def main():
    """Main conversion function."""
    # Get paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    md_file = repo_root / "TROUBLESHOOTING.md"
    html_file = repo_root / "TROUBLESHOOTING.html"
    
    print(f"Reading {md_file}...")
    
    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    print("Converting to HTML...")
    
    # Convert to HTML
    html_content = markdown_to_html(markdown_content)
    
    # Wrap in template
    full_html = create_html_template(html_content)
    
    # Write HTML file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ Created {html_file}")
    print(f"  File size: {html_file.stat().st_size} bytes")
    print(f"  This HTML file can be opened directly in any Windows browser")
    print(f"  Double-click the file to view it")


if __name__ == "__main__":
    main()

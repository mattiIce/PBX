# Windows-Compatible Troubleshooting Guide

## Overview

The file `TROUBLESHOOTING.html` is a Windows-compatible version of the troubleshooting guide that can be opened directly in any web browser on Windows systems.

## Features

- **Standalone HTML file** - No dependencies, internet connection, or web server required
- **Professional styling** - Clean, modern design with proper typography
- **Fully formatted** - All markdown features converted to HTML:
  - Headers and subheaders
  - Code blocks with syntax highlighting
  - Tables with proper styling
  - Lists (ordered and unordered)
  - Links and navigation
  - Horizontal rules
- **Windows-friendly** - Double-click to open in your default browser
- **Print-ready** - Optimized for printing if needed
- **Responsive design** - Works on different screen sizes

## How to Use on Windows

### Method 1: Double-Click (Easiest)
1. Navigate to the PBX folder in Windows Explorer
2. Find `TROUBLESHOOTING.html`
3. Double-click the file
4. It will open in your default web browser (Chrome, Edge, Firefox, etc.)

### Method 2: Right-Click Menu
1. Right-click on `TROUBLESHOOTING.html`
2. Select "Open with"
3. Choose your preferred browser

### Method 3: From Browser
1. Open your web browser
2. Press `Ctrl+O` (or use File → Open)
3. Navigate to and select `TROUBLESHOOTING.html`

## Navigation

The HTML file includes:
- **Table of Contents** with clickable links to jump to any section
- **Section headers** that are easy to scan
- **Color-coded code blocks** for different languages (bash, yaml, python)
- **Styled tables** for quick reference information

## Updating the HTML File

If `TROUBLESHOOTING.md` is updated, you can regenerate the HTML file by running:

```bash
python scripts/convert_troubleshooting_to_html.py
```

This will create a fresh `TROUBLESHOOTING.html` file with the latest content.

## Browser Compatibility

The HTML file works with all modern browsers:
- ✅ Google Chrome
- ✅ Microsoft Edge
- ✅ Mozilla Firefox
- ✅ Opera
- ✅ Safari
- ✅ Internet Explorer 11+ (with limited CSS support)

## File Details

- **Original file**: `TROUBLESHOOTING.md` (Markdown format)
- **Windows copy**: `TROUBLESHOOTING.html` (Standalone HTML)
- **Conversion script**: `scripts/convert_troubleshooting_to_html.py`

## Benefits Over Markdown File

1. **No special viewer required** - Opens directly in any browser
2. **Better formatting** - Professional appearance with colors and styling
3. **Easier navigation** - Clickable table of contents
4. **More accessible** - Can be viewed by anyone with a browser
5. **Shareable** - Can be sent via email and opened without special tools

## Troubleshooting

### File won't open
- Make sure you have a web browser installed
- Try right-clicking and selecting "Open with" → Choose a browser

### Formatting looks wrong
- Use a modern browser (Chrome, Edge, Firefox)
- Avoid Internet Explorer if possible

### Need to print
- Open the file in your browser
- Use `Ctrl+P` or File → Print
- The page is optimized for printing

## Original Markdown File

The original `TROUBLESHOOTING.md` file remains unchanged and can still be:
- Viewed on GitHub with proper formatting
- Edited with any text editor
- Used with markdown viewers
- Version controlled with Git

Both files serve the same purpose but for different use cases:
- Use **TROUBLESHOOTING.md** for editing and version control
- Use **TROUBLESHOOTING.html** for easy viewing on Windows

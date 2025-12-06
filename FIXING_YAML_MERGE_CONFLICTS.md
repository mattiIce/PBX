# Fixing YAML Merge Conflicts in config.yml

## Problem

When Git merge conflicts occur in YAML files like `config.yml`, Git adds conflict markers that break YAML syntax:

```yaml
<<<<<<< Updated upstream
  sip_port: 5060
=======
  sip_port: 5061
>>>>>>> Stashed changes
```

These markers (`<<<<<<<`, `=======`, `>>>>>>>`) are not valid YAML and will cause parsing errors like:

```
security check failed while scanning a simple key in config.yml line 14 column 1,
could not find expected ":" in config.yml, line 15 column 1
```

## Solution

### 1. Identify the Conflict

Search for Git conflict markers in the file:

```bash
grep -n "^<<<<<<<\|^>>>>>>>\|^=======" config.yml
```

Or look for these patterns:
- `<<<<<<< Updated upstream` or `<<<<<<< HEAD`
- `=======`
- `>>>>>>> Stashed changes` or `>>>>>>> branch-name`

### 2. Resolve the Conflict

For each conflict section:

1. **Review both versions** - the content between `<<<<<<< Updated upstream` and `=======` is the current branch version, and between `=======` and `>>>>>>> Stashed changes` is the incoming change

2. **Decide which version to keep** (or merge them manually)

3. **Remove the conflict markers** completely

Example - Before:
```yaml
server:
  sip_host: 0.0.0.0
<<<<<<< Updated upstream
  sip_port: 5060
  external_ip: 192.168.1.14
=======
  sip_port: 5061
  external_ip: 192.168.1.15
>>>>>>> Stashed changes
  rtp_port_range_start: 10000
```

After (keeping upstream version):
```yaml
server:
  sip_host: 0.0.0.0
  sip_port: 5060
  external_ip: 192.168.1.14
  rtp_port_range_start: 10000
```

### 3. Validate the YAML

After resolving conflicts, validate the YAML syntax:

```bash
# Using Python
python3 -c "import yaml; yaml.safe_load(open('config.yml'))" && echo "Valid YAML"

# Using yamllint (if installed)
yamllint config.yml
```

### 4. Test the Configuration

Start the PBX system to ensure the configuration loads correctly:

```bash
python3 main.py
```

## Prevention

To minimize merge conflicts in `config.yml`:

1. **Use environment variables** for values that differ between environments (already configured in the file with `${VAR_NAME}` syntax)

2. **Communicate changes** with your team before modifying shared configuration

3. **Pull before editing** to ensure you have the latest version

4. **Keep changes small** and focused on specific configuration sections

## Additional Fixes Applied

While resolving the merge conflict issue, the following YAML formatting improvements were also made:

1. **Removed trailing spaces** - Empty comment lines and line endings had trailing spaces removed
2. **Fixed indentation** - List items under `extensions:` and `queues:` are now properly indented by 2 spaces
3. **Consistent formatting** - Applied consistent YAML style throughout the file

These changes ensure the file passes YAML linters and follows best practices.

## Tools

### Recommended YAML Validation Tools

- **PyYAML** (Python) - Built into the PBX system
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('config.yml'))"
  ```

- **yamllint** - Comprehensive YAML linter
  ```bash
  yamllint config.yml
  # Or with relaxed rules
  yamllint -d relaxed config.yml
  ```

- **VS Code Extensions**:
  - YAML (Red Hat) - Provides syntax highlighting and validation
  - YAML Lint - Real-time linting

## References

- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [YAML Specification](https://yaml.org/spec/)
- [Git Merge Conflicts Guide](https://git-scm.com/docs/git-merge#_how_conflicts_are_presented)

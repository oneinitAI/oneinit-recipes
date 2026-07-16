# OneInit Recipes

Community recipe registry for [OneInit](https://github.com/BG4JTS/oneinit).

## Structure

```
INDEX.json              Global package index
recipes/
  <package-name>/
    <version>.yaml      Recipe file
```

## Usage

```bash
# Update local index
oneinit update

# Search available recipes
oneinit search

# Install a recipe
oneinit install <package-name>
```

## Contribute a Recipe

1. Write a recipe YAML file (see format below)
2. Validate locally: `oneinit verify my-recipe.yaml`
3. Publish: `oneinit publish my-recipe.yaml`
4. Follow the output steps to submit a PR

### Recipe Format

```yaml
name: my-tool
version: "1.0.0"
description: "A tool description"

platforms:
  windows:
    url: "https://example.com/tool-1.0.0.zip"
    sha256: "64-char-hex-string"
    install_type: "zip_extract"
    install_path: "my-tool"
    path_add: ["{{install_dir}}"]

post_install:
  config_files:
    - path: "config.ini"
      template: "setting = {{mirror_pip}}"
  commands:
    - "echo done"

tags:
  - "utility"

maintainer:
  name: "Your Name"
  github: "yourname"
```

### Template Variables

- `{{install_dir}}` - Install directory path
- `{{user_home}}` - User home directory
- `{{mirror_pip}}` - `https://pypi.tuna.tsinghua.edu.cn/simple`
- `{{mirror_pip_host}}` - `pypi.tuna.tsinghua.edu.cn`
- `{{mirror_npm}}` - `https://registry.npmmirror.com`

### Supported install_type

`zip_extract`, `tar_extract`, `exe_silent`, `binary_copy`, `msi_install`, `pkg_install`

## License

GPL-3.0

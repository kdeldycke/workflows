# {octicon}`download` Installation

```{sidebar}
[![Packaging status](https://repology.org/badge/vertical-allrepos/python%3Arepomatic.svg)](https://repology.org/project/python%3Arepomatic/versions)
```

## Quick start

```shell-session
$ cd my-project
$ uvx -- repomatic init
$ git add .
$ git commit -m "Update repomatic files"
$ git push
```

Works for both new and existing repositories. Run `repomatic init --help` to see available components and options: the workflows then take it from there, opening issues and PRs to guide any remaining setup.

## Try it

Thanks to `uv`, you can run it in one command, without installation or venv:

`````{tab-set}

````{tab-item} Latest release
```shell-session
$ uvx -- repomatic --help
```
````

````{tab-item} Specific version
```shell-session
$ uvx -- repomatic==6.13.0 --help
```
````

````{tab-item} Development version
```shell-session
$ uvx --from "repomatic @ git+https://github.com/kdeldycke/repomatic" -- repomatic --help
```
````

`````

## Install methods

`repomatic` is available on a couple of package managers:

`````{tab-set}

````{tab-item} uv
Easiest way is to [install `uv`](https://docs.astral.sh/uv/getting-started/installation/), then install `repomatic` system-wide with the [`uv tool`](https://docs.astral.sh/uv/guides/tools/#installing-tools) command:

```{code-block} shell-session
$ uv tool install repomatic
```
````

````{tab-item} pip
You can install the latest stable release and its dependencies with a simple `pip` call:

```{code-block} shell-session
$ python -m pip install repomatic
```

If you have difficulties to use `pip`, see [`pip`'s own installation instructions](https://pip.pypa.io/en/stable/installation/).
````

````{tab-item} pipx
[`pipx`](https://pipx.pypa.io/stable/installation/) is a great way to install Python applications globally:

```{code-block} shell-session
$ pipx install repomatic
```
````

````{tab-item} Arch Linux
A `repomatic` package is [available on AUR](https://aur.archlinux.org/packages/python-repomatic) and can be installed with any AUR helper:

```{code-block} shell-session
$ yay -S python-repomatic
```

```{code-block} shell-session
$ paru -S python-repomatic
```

```{code-block} shell-session
$ pacaur -S python-repomatic
```
````

`````

## Executables

To ease deployment, standalone executables of `repomatic`'s latest version are available as direct downloads for several platforms and architectures:

| Platform    | `arm64`                                                                                                                                              | `x86_64`                                                                                                                                         |
| :---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Linux**   | [Download `repomatic-6.13.0-linux-arm64.bin`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-linux-arm64.bin)     | [Download `repomatic-6.13.0-linux-x64.bin`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-linux-x64.bin)     |
| **macOS**   | [Download `repomatic-6.13.0-macos-arm64.bin`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-macos-arm64.bin)     | [Download `repomatic-6.13.0-macos-x64.bin`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-macos-x64.bin)     |
| **Windows** | [Download `repomatic-6.13.0-windows-arm64.exe`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-windows-arm64.exe) | [Download `repomatic-6.13.0-windows-x64.exe`](https://github.com/kdeldycke/repomatic/releases/download/v6.13.0/repomatic-6.13.0-windows-x64.exe) |

That way you have a chance to try it out without installing Python or `uv`. Or embed it in your CI/CD pipelines running on minimal images. Or run it on old platforms without worrying about dependency hell.

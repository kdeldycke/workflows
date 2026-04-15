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

This **works for both new and existing repositories** — managed files (workflows, configs, skills) are always regenerated to the latest version. The only exception is `changelog.md`, which is never overwritten once it exists. The workflows will start running and guide you through any remaining setup (like [creating a `REPOMATIC_PAT` secret](security.md#permissions-and-token)) via issues and PRs in your repository. After that, the [autofix workflow](workflows.md#github-workflows-autofix-yaml-jobs) handles ongoing sync.

Run `repomatic init --help` to see available components and options.

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

`````{tab-set}

````{tab-item} uv
```shell-session
$ uv tool install repomatic
```
````

````{tab-item} pipx
```shell-session
$ pipx install repomatic
```
````

````{tab-item} pip
```shell-session
$ pip install repomatic
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

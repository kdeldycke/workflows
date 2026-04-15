# {octicon}`command-palette` CLI parameters

## Help screen

```{eval-rst}
.. click:run::
    from repomatic.cli import repomatic
    invoke(repomatic, args=["--help"])
```

## Options

```{eval-rst}
.. click:: repomatic.cli:repomatic
    :prog: repomatic
    :nested: full
```

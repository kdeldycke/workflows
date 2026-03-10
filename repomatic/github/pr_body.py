# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""Generate PR body with workflow metadata for auto-created pull requests.

Uses :class:`~repomatic.metadata.Metadata` for CI context to produce a
collapsible ``<details>`` block containing a metadata table. Template prefixes
are loaded from markdown files in ``repomatic/templates/``, optionally with
YAML frontmatter for templates that require arguments.
"""

from __future__ import annotations

import re
from importlib.resources import as_file, files
from string import Template

from ..metadata import Metadata


def _unescape_dollars(text: str) -> str:
    r"""Replace ``\$`` with ``$`` in template text.

    .. caution::
        Workaround for mdformat escaping ``$`` characters in markdown files.
        Templates use ``string.Template`` (``$variable`` syntax), but mdformat
        rewrites ``$var`` as ``\$var``. We undo this at load time so that
        ``string.Template.substitute()`` sees the original placeholders.
    """
    return text.replace(r"\$", "$")


def _parse_frontmatter(raw: str) -> tuple[dict[str, object], str]:
    """Split a template file into YAML frontmatter and markdown body.

    :param raw: Raw template file content.
    :return: A tuple of (frontmatter dict, body string).
    """
    if not raw.startswith("---"):
        return {}, _unescape_dollars(raw)

    # Find the closing --- delimiter.
    end = raw.index("---", 3)
    yaml_block = raw[3:end].strip()
    body = _unescape_dollars(raw[end + 3 :].lstrip("\n"))

    # Minimal YAML parsing: supports ``key: value`` and ``key: [items]``.
    meta: dict[str, object] = {}
    for line in yaml_block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1]
            meta[key.strip()] = (
                [item.strip() for item in items.split(",") if item.strip()]
                if items.strip()
                else []
            )
        else:
            # Strip surrounding quotes from YAML string values.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            meta[key.strip()] = value

    return meta, body


def load_template(name: str) -> tuple[dict[str, object], str]:
    """Load a PR body template from the ``repomatic/templates/`` package.

    :param name: Template name without ``.md`` extension (e.g. ``bump-version``).
    :return: A tuple of (frontmatter metadata dict, template body string).
    :raises FileNotFoundError: If the template file doesn't exist.
    """
    template_files = files("repomatic.templates")
    with as_file(template_files.joinpath(f"{name}.md")) as path:
        raw = path.read_text(encoding="UTF-8")
    return _parse_frontmatter(raw)


def _substitute(text: str, kwargs: dict[str, str | None]) -> str:
    """Apply ``string.Template`` substitution if kwargs are provided.

    ``None`` values are normalized to empty strings so callers can pass
    :class:`~repomatic.metadata.Metadata` properties directly without
    coercing at the call site.
    """
    if kwargs:
        safe = {k: (v if v is not None else "") for k, v in kwargs.items()}
        return Template(text).substitute(safe)
    return text


def _render_single(name: str, kwargs: dict[str, str | None]) -> tuple[str, bool]:
    """Render a single template and return its body with footer preference.

    :param name: Template name without ``.md`` extension.
    :param kwargs: Variables to substitute into the template.
    :return: A tuple of (rendered body, wants_footer).
    """
    meta, body = load_template(name)
    result = _substitute(body, kwargs).strip()
    wants_footer = meta.get("footer") != "false" and name != "generated-footer"
    return result, wants_footer


def render_template(*names: str, **kwargs: str | None) -> str:
    """Load and render one or more templates with variable substitution.

    When multiple template names are given, each is rendered and joined with
    a blank line. The ``generated-footer`` attribution is appended
    once at the end if **any** of the templates wants it (i.e. does not have
    ``footer: false`` in its frontmatter).

    Static templates (no ``$variable`` placeholders) are returned as-is.
    Dynamic templates use ``string.Template`` (``$variable`` syntax) to avoid
    conflicts with markdown braces like ``[tool.repomatic]``.

    Consecutive blank lines left by empty variables are collapsed to a single
    blank line.

    :param names: One or more template names without ``.md`` extension.
    :param kwargs: Variables to substitute into all templates.
    :return: The rendered markdown string.
    """
    parts = []
    append_footer = False
    for name in names:
        body, wants_footer = _render_single(name, kwargs)
        parts.append(body)
        if wants_footer:
            append_footer = True
    result = "\n\n".join(parts)
    if append_footer:
        result += "\n\n---\n\n" + render_template("generated-footer")
    result = re.sub(r"\n{3,}", "\n\n", result)
    if append_footer:
        result += "\n"
    return result


def render_title(name: str, **kwargs: str | None) -> str:
    """Load and render a template's PR title with variable substitution.

    :param name: Template name without ``.md`` extension.
    :param kwargs: Variables to substitute into the title.
    :return: The rendered title string.
    :raises KeyError: If the template has no ``title`` in its frontmatter.
    """
    meta, _body = load_template(name)
    title = meta.get("title")
    if not title or not isinstance(title, str):
        msg = f"Template {name!r} has no 'title' in frontmatter"
        raise KeyError(msg)
    return _substitute(title, kwargs)


def render_commit_message(name: str, **kwargs: str | None) -> str:
    """Load and render a template's commit message with variable substitution.

    Falls back to the ``title`` if no ``commit_message`` is defined.

    :param name: Template name without ``.md`` extension.
    :param kwargs: Variables to substitute into the commit message.
    :return: The rendered commit message string.
    """
    meta, _body = load_template(name)
    commit_msg = meta.get("commit_message")
    if commit_msg and isinstance(commit_msg, str):
        return _substitute(commit_msg, kwargs)
    # Fall back to title.
    return render_title(name, **kwargs)


def template_args(name: str) -> list[str]:
    """Return the list of required arguments for a template.

    :param name: Template name without ``.md`` extension.
    :return: List of argument names from the frontmatter ``args`` field.
    """
    meta, _body = load_template(name)
    args = meta.get("args", [])
    if isinstance(args, list):
        return args
    return []


def get_template_names() -> list[str]:
    """Discover all available template names from the templates package.

    :return: Sorted list of template names (without ``.md`` extension).
    """
    template_dir = files("repomatic.templates")
    names = []
    for item in template_dir.iterdir():
        item_name = getattr(item, "name", str(item))
        if item_name.endswith(".md"):
            names.append(item_name.removesuffix(".md"))
    return sorted(names)


def extract_workflow_filename(workflow_ref: str | None) -> str:
    """Extract the workflow filename from ``GITHUB_WORKFLOW_REF``.

    :param workflow_ref: The full workflow reference, e.g.
        ``owner/repo/.github/workflows/name.yaml@refs/heads/branch``.
    :return: The workflow filename (e.g. ``name.yaml``), or an empty string
        if the reference is empty or malformed.
    """
    if not workflow_ref:
        return ""
    # Strip the @ref suffix, then take the basename.
    path_part = workflow_ref.split("@")[0]
    return path_part.rsplit("/", 1)[-1] if "/" in path_part else path_part


def generate_pr_metadata_block() -> str:
    """Generate a collapsible metadata block from CI context.

    Uses :class:`~repomatic.metadata.Metadata` to read ``GITHUB_*``
    environment variables and returns a markdown ``<details>`` block
    containing a table of workflow metadata fields.

    :return: A markdown string with the metadata block.
    """
    md = Metadata()

    sha = md.sha or ""
    actor = md.event_actor or ""
    triggering_actor = md.triggering_actor
    rerun_row = ""
    if triggering_actor and triggering_actor != actor:
        rerun_row = f"| **Re-run by** | @{triggering_actor} |\n"

    return render_template(
        "pr-metadata",
        event_name=md.event_name,
        actor=actor,
        rerun_row=rerun_row,
        ref_name=md.ref_name,
        repo_url=md.repo_url,
        sha=sha,
        sha_short=sha[:8],
        job=md.job_name,
        workflow_file=extract_workflow_filename(md.workflow_ref),
        run_id=md.run_id,
        run_number=md.run_number,
        run_attempt=md.run_attempt,
    )


def _repo_url() -> str | None:
    """Build repository URL from CI context.

    Delegates to :attr:`Metadata.repo_url <repomatic.metadata.Metadata.repo_url>`.
    """
    return Metadata().repo_url


def generate_refresh_tip() -> str:
    """Generate a tip admonition inviting users to refresh the PR manually.

    Uses :class:`~repomatic.metadata.Metadata` for the repository URL and
    ``GITHUB_WORKFLOW_REF`` to build the workflow dispatch URL.

    :return: A GitHub-flavored markdown ``[!TIP]`` blockquote, or an empty
        string if the workflow reference is unavailable.
    """
    md = Metadata()
    workflow_file = extract_workflow_filename(md.workflow_ref)
    if not workflow_file:
        return ""
    return render_template(
        "refresh-tip", repo_url=md.repo_url, workflow_file=workflow_file,
    )


def build_pr_body(prefix: str, metadata_block: str) -> str:
    """Concatenate prefix, refresh tip, and metadata block into a PR body.

    The ``metadata_block`` already includes the attribution footer (appended
    automatically by :func:`render_template`).

    :param prefix: Content to prepend before the metadata block. Can be empty.
    :param metadata_block: The collapsible metadata block from
        :func:`generate_pr_metadata_block`, with footer.
    :return: The complete PR body string.
    """
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    tip = generate_refresh_tip()
    if tip:
        parts.append(tip)
    parts.append(metadata_block)
    return "\n\n\n".join(parts)

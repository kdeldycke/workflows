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

from __future__ import annotations

from pathlib import Path

import pytest

from gha_utils.deps_graph import (
    _compute_node_degrees,
    _compute_node_depths,
    _compute_subtree_sizes,
    build_dependency_graph,
    filter_graph_to_package,
    get_available_extras,
    get_available_groups,
    normalize_package_name,
    parse_bom_ref,
    render_mermaid,
    trim_graph_to_depth,
)


# Sample CycloneDX SBOM data for testing.
SAMPLE_SBOM = {
    "metadata": {
        "component": {
            "bom-ref": "my-project-1@1.0.0",
            "name": "my-project",
            "version": "1.0.0",
        }
    },
    "components": [
        {"bom-ref": "click-2@8.0.0", "name": "click", "version": "8.0.0"},
        {"bom-ref": "requests-3@2.28.0", "name": "requests", "version": "2.28.0"},
        {"bom-ref": "urllib3-4@1.26.0", "name": "urllib3", "version": "1.26.0"},
        {"bom-ref": "certifi-5@2022.0", "name": "certifi", "version": "2022.0"},
    ],
    "dependencies": [
        {
            "ref": "my-project-1@1.0.0",
            "dependsOn": ["click-2@8.0.0", "requests-3@2.28.0"],
        },
        {"ref": "click-2@8.0.0", "dependsOn": []},
        {
            "ref": "requests-3@2.28.0",
            "dependsOn": ["urllib3-4@1.26.0", "certifi-5@2022.0"],
        },
        {"ref": "urllib3-4@1.26.0", "dependsOn": []},
        {"ref": "certifi-5@2022.0", "dependsOn": []},
    ],
}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("click", "click_0"),  # Reserved Mermaid keyword.
        ("click-extra", "click_extra"),
        ("My-Package", "my_package"),
        ("package123", "package123"),
        ("foo.bar", "foo_bar"),
        ("foo_bar", "foo_bar"),
        ("graph", "graph_0"),  # Reserved Mermaid keyword.
        ("end", "end_0"),  # Reserved Mermaid keyword.
    ],
)
def test_normalize_package_name(name: str, expected: str) -> None:
    assert normalize_package_name(name) == expected


@pytest.mark.parametrize(
    ("bom_ref", "expected_name", "expected_version"),
    [
        ("click-2@8.0.0", "click", "8.0.0"),
        ("click-extra-11@7.4.0", "click-extra", "7.4.0"),
        ("my-project-1@1.0.0", "my-project", "1.0.0"),
        ("simple@1.0", "simple", "1.0"),
        ("no-version-123", "no-version", ""),
        ("urllib3-4@1.26.0", "urllib3", "1.26.0"),
    ],
)
def test_parse_bom_ref(bom_ref: str, expected_name: str, expected_version: str) -> None:
    name, version = parse_bom_ref(bom_ref)
    assert name == expected_name
    assert version == expected_version


def test_build_dependency_graph() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    assert root_name == "my-project"
    assert len(nodes) == 5  # root + 4 components.

    # Check nodes contain expected packages.
    node_names = {name for name, _ in nodes.values()}
    assert "my-project" in node_names
    assert "click" in node_names
    assert "requests" in node_names
    assert "urllib3" in node_names
    assert "certifi" in node_names

    # Check edges.
    assert ("my-project", "click") in edges
    assert ("my-project", "requests") in edges
    assert ("requests", "urllib3") in edges
    assert ("requests", "certifi") in edges
    assert len(edges) == 4


def test_filter_graph_to_package() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    # Filter to requests package.
    filtered_nodes, filtered_edges = filter_graph_to_package(
        root_name, nodes, edges, "requests"
    )

    # Should only include requests and its dependencies.
    filtered_names = {name for name, _ in filtered_nodes.values()}
    assert "requests" in filtered_names
    assert "urllib3" in filtered_names
    assert "certifi" in filtered_names
    assert "my-project" not in filtered_names
    assert "click" not in filtered_names

    # Check edges.
    assert ("requests", "urllib3") in filtered_edges
    assert ("requests", "certifi") in filtered_edges
    assert len(filtered_edges) == 2


def test_trim_graph_to_depth_zero() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    # Depth 0 = root only.
    trimmed_nodes, trimmed_edges = trim_graph_to_depth(root_name, nodes, edges, 0)

    trimmed_names = {name for name, _ in trimmed_nodes.values()}
    assert trimmed_names == {"my-project"}
    assert trimmed_edges == []


def test_trim_graph_to_depth_one() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    # Depth 1 = root + primary deps.
    trimmed_nodes, trimmed_edges = trim_graph_to_depth(root_name, nodes, edges, 1)

    trimmed_names = {name for name, _ in trimmed_nodes.values()}
    assert trimmed_names == {"my-project", "click", "requests"}
    # Only edges from root to primary deps.
    assert ("my-project", "click") in trimmed_edges
    assert ("my-project", "requests") in trimmed_edges
    assert len(trimmed_edges) == 2


def test_trim_graph_to_depth_two() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    # Depth 2 = root + primary deps + their deps.
    trimmed_nodes, trimmed_edges = trim_graph_to_depth(root_name, nodes, edges, 2)

    trimmed_names = {name for name, _ in trimmed_nodes.values()}
    assert trimmed_names == {"my-project", "click", "requests", "urllib3", "certifi"}
    assert len(trimmed_edges) == 4


def test_trim_graph_to_depth_exceeding() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)

    # Depth larger than the graph keeps everything.
    trimmed_nodes, trimmed_edges = trim_graph_to_depth(root_name, nodes, edges, 100)

    trimmed_names = {name for name, _ in trimmed_nodes.values()}
    assert len(trimmed_names) == 5
    assert len(trimmed_edges) == len(edges)


def test_render_mermaid() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    output = render_mermaid(root_name, nodes, edges)

    assert output.startswith("flowchart LR")
    # "click" is a reserved Mermaid keyword, so it gets "_0" suffix.
    # Primary deps use hexagon shape with markdown backticks.
    assert 'click_0{{"`click`"}}' in output
    # Root uses subprocess (subroutine) shape.
    assert 'my_project[["`my-project`"]]' in output
    # Versions are not included in node labels.
    assert "v8.0.0" not in output
    # Primary dependencies are in a subgraph for vertical alignment.
    assert "subgraph primary-deps [Primary dependencies]" in output
    # Primary dependencies use thick arrows.
    assert "my_project ==> click_0" in output
    assert "my_project ==> requests" in output
    # Transitive dependencies use normal arrows.
    assert "requests --> urllib3" in output
    # PyPI links are added for each package.
    assert 'click click_0 "https://pypi.org/project/click/" _blank' in output
    assert 'click requests "https://pypi.org/project/requests/" _blank' in output


def test_render_mermaid_with_specifiers() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    # Provide specifiers for edge labels.
    specifiers = {
        "my-project": {"click": ">=8.0", "requests": ">=2.28"},
        "requests": {"urllib3": ">=1.26,<2", "certifi": ">=2022"},
    }
    output = render_mermaid(root_name, nodes, edges, specifiers=specifiers)

    # Check edge labels with specifiers.
    assert 'my_project ==>|" >=8.0 "| click_0' in output
    assert 'my_project ==>|" >=2.28 "| requests' in output
    assert 'requests -->|" >=1.26,<2 "| urllib3' in output
    assert 'requests -->|" >=2022 "| certifi' in output


def test_render_mermaid_with_groups() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    # Add a test package to a group.
    group_packages = {"test": {"pytest"}}
    # Add pytest to nodes and edges.
    extended_nodes = dict(nodes)
    extended_nodes["pytest-6@7.0.0"] = ("pytest", "7.0.0")
    extended_edges = list(edges) + [("my-project", "pytest")]

    output = render_mermaid(root_name, extended_nodes, extended_edges, group_packages)

    # Group subgraph ID is prefixed to avoid collision with node IDs.
    assert "subgraph grp_test [--group test]" in output
    # Root uses dashed arrow to group subgraph.
    assert "my_project -.-> grp_test" in output


def test_render_mermaid_with_subgraph_specifiers() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    # Add test packages to a group.
    group_packages = {"test": {"pytest", "coverage"}}
    extended_nodes = dict(nodes)
    extended_nodes["pytest-6@7.0.0"] = ("pytest", "7.0.0")
    extended_nodes["coverage-7@7.0.0"] = ("coverage", "7.0.0")
    extended_edges = list(edges) + [
        ("my-project", "pytest"),
        ("my-project", "coverage"),
    ]
    # Specifiers for primary deps in the test group.
    subgraph_specifiers = {"test": {"pytest": ">=9", "coverage": ">=7.11"}}

    output = render_mermaid(
        root_name,
        extended_nodes,
        extended_edges,
        group_packages,
        subgraph_specifiers=subgraph_specifiers,
    )

    # Primary group deps use hexagon shape with specifier in label.
    assert 'pytest{{"`pytest >=9`"}}' in output
    assert 'coverage{{"`coverage >=7.11`"}}' in output


def test_render_mermaid_primary_deps_in_subgraph() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    # Add test packages: pytest and pytest-cov (primary), iniconfig (transitive).
    group_packages = {"test": {"pytest", "pytest-cov", "iniconfig"}}
    extended_nodes = dict(nodes)
    extended_nodes["pytest-6@7.0.0"] = ("pytest", "7.0.0")
    extended_nodes["pytest-cov-8@7.0.0"] = ("pytest-cov", "7.0.0")
    extended_nodes["iniconfig-9@2.0.0"] = ("iniconfig", "2.0.0")
    extended_edges = list(edges) + [
        ("my-project", "pytest"),
        ("my-project", "pytest-cov"),
        ("my-project", "iniconfig"),
        ("pytest-cov", "pytest"),
        ("pytest", "iniconfig"),
    ]
    # pytest and pytest-cov are primary deps (in subgraph_specifiers).
    subgraph_specifiers = {"test": {"pytest": ">=9", "pytest-cov": ">=7"}}

    output = render_mermaid(
        root_name,
        extended_nodes,
        extended_edges,
        group_packages,
        subgraph_specifiers=subgraph_specifiers,
    )

    # Primary deps use hexagon shape.
    assert 'pytest{{"`pytest >=9`"}}' in output
    assert 'pytest_cov{{"`pytest-cov >=7`"}}' in output
    # Transitive dep uses round shape.
    assert 'iniconfig(["`iniconfig`"])' in output
    # Arrow pointing to a primary dep uses thick style.
    assert "pytest_cov ==> pytest" in output
    # Arrow pointing to a transitive dep uses normal style.
    assert "pytest --> iniconfig" in output


def test_render_mermaid_with_extras() -> None:
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    # Add a package to an extra.
    extra_packages = {"xml": {"lxml"}}
    # Add lxml to nodes and edges.
    extended_nodes = dict(nodes)
    extended_nodes["lxml-7@4.9.0"] = ("lxml", "4.9.0")
    extended_edges = list(edges) + [("my-project", "lxml")]

    output = render_mermaid(
        root_name, extended_nodes, extended_edges, extra_packages=extra_packages
    )

    # Extra subgraph ID is prefixed to avoid collision with node IDs.
    assert "subgraph ext_xml [--extra xml]" in output
    # Root uses dashed arrow to extra subgraph.
    assert "my_project -.-> ext_xml" in output


def test_compute_node_degrees() -> None:
    _, _, edges = build_dependency_graph(SAMPLE_SBOM)
    degrees = _compute_node_degrees(edges)
    # requests: 1 out (from root) + 2 out (urllib3, certifi) = degree 3.
    assert degrees["requests"] == 3
    # click: 1 in (from root) = degree 1.
    assert degrees["click"] == 1
    # root: 2 out (click, requests) = degree 2.
    assert degrees["my-project"] == 2


def test_compute_subtree_sizes() -> None:
    _, _, edges = build_dependency_graph(SAMPLE_SBOM)
    subtree = _compute_subtree_sizes(edges)
    # requests has 2 descendants: urllib3 and certifi.
    assert subtree["requests"] == 2
    # click has 0 descendants.
    assert subtree["click"] == 0
    # Leaf nodes have 0 descendants.
    assert subtree["urllib3"] == 0
    assert subtree["certifi"] == 0


def test_compute_node_depths() -> None:
    root_name, _, edges = build_dependency_graph(SAMPLE_SBOM)
    depths = _compute_node_depths(root_name, edges)
    assert depths["my-project"] == 0
    assert depths["click"] == 1
    assert depths["requests"] == 1
    assert depths["urllib3"] == 2
    assert depths["certifi"] == 2


def test_render_mermaid_primary_deps_ordering() -> None:
    """Primary deps with larger subtrees should be declared first."""
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    output = render_mermaid(root_name, nodes, edges)
    # requests (subtree=2) should appear before click (subtree=0).
    lines = output.splitlines()
    requests_idx = next(i for i, line in enumerate(lines) if "requests{{" in line)
    click_idx = next(i for i, line in enumerate(lines) if "click_0{{" in line)
    assert requests_idx < click_idx


def test_render_mermaid_edge_ordering() -> None:
    """Root edges should come before transitive edges."""
    root_name, nodes, edges = build_dependency_graph(SAMPLE_SBOM)
    output = render_mermaid(root_name, nodes, edges)
    lines = output.splitlines()
    # Find edge lines (contain ==> or -->).
    edge_lines = [line.strip() for line in lines if "==>" in line or "-->" in line]
    # Root edges (my_project ==>) should come before transitive edges.
    root_edge_indices = [
        i for i, line in enumerate(edge_lines) if line.startswith("my_project")
    ]
    transitive_edge_indices = [
        i for i, line in enumerate(edge_lines) if not line.startswith("my_project")
    ]
    if root_edge_indices and transitive_edge_indices:
        assert max(root_edge_indices) < min(transitive_edge_indices)

    # Among root edges, requests (degree=3) should come before click (degree=1).
    root_edges = [edge_lines[i] for i in root_edge_indices]
    requests_edge = next(i for i, line in enumerate(root_edges) if "requests" in line)
    click_edge = next(i for i, line in enumerate(root_edges) if "click_0" in line)
    assert requests_edge < click_edge


def test_get_available_groups() -> None:
    # Test against the actual pyproject.toml in the repo.
    groups = get_available_groups()
    # Should discover test and typing groups.
    assert "test" in groups
    assert "typing" in groups


def test_get_available_extras(tmp_path: Path) -> None:
    # Use a temporary pyproject.toml with known extras.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project.optional-dependencies]\n"
        'xml = ["click-extra [xml]"]\n'
        'yaml = ["click-extra [yaml]"]\n'
        'json5 = ["click-extra [json5]"]\n'
    )
    extras = get_available_extras(pyproject)
    assert "xml" in extras
    assert "yaml" in extras
    assert "json5" in extras

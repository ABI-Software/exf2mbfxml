# from collections import defaultdict
from exf2mbfxml.utilities import nest_sequence, duplicate_structure
from exf2mbfxml.zinc import get_point, get_colour, get_resolution, get_group_nodes

from typing import Union, List, Dict, Set
from collections import defaultdict
# from pprint import pprint

Branch = Union[int, List["Branch"]]


def build_subtree_map(tree: Branch, node_to_subtree: Dict[int, Set[int]] = None) -> Dict[int, Set[int]]:
    if node_to_subtree is None:
        node_to_subtree = defaultdict(set)

    def helper(node: Branch, parent=None) -> Set[int]:
        if isinstance(node, int):
            node_to_subtree[node].add(node)
            return {node}
        else:
            all_nodes = set()
            for child in node:
                child_nodes = helper(child)
                all_nodes.update(child_nodes)
            if isinstance(node[0], int):  # mark the first node as the parent
                node_to_subtree[node[0]].update(all_nodes)
            return all_nodes

    helper(tree)
    return node_to_subtree


def trim_groups(group_dict: Dict[str, Set[int]], node_to_subtree: Dict[int, Set[int]]) -> Dict[str, Set[int]]:
    trimmed = {}
    for label, points in group_dict.items():
        # Find smallest subtree that contains all group points
        candidates = []
        for node, subtree in node_to_subtree.items():
            if points.issubset(subtree):
                candidates.append((node, subtree))

        if candidates:
            # Use the smallest subtree (most specific)
            best_node, best_subtree = min(candidates, key=lambda item: len(item[1]))
            # Remove the best_node itself if it's not truly part of the group
            cleaned = points.intersection(best_subtree - {best_node})
            trimmed[label] = cleaned
        else:
            # fallback if no matching subtree
            trimmed[label] = points
    return trimmed


# # Your initial input
# initial_tree = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, 15, 16, 17, 18]]
#
# group_dict = {
#     'Bob': {8, 13, 14},
#     'Dave': {8, 9, 10, 11},
#     'Dendrite': set(range(1, 19)),
#     'FIL: Filaments 1': set(range(1, 19)),
#     'http://uri.interlex.org/base/ilx_0777077': set(range(1, 19)),
#     'http://uri.interlex.org/base/ilx_0777078': {2, 3, 4},
#     'http://uri.interlex.org/base/ilx_0777079': {3, 4, 5},
#     'http://uri.interlex.org/base/ilx_0777080': {4, 5, 6, 7, 8, 9, 13},
#     'http://uri.interlex.org/base/ilx_0777081': {8, 9, 10, 11},
#     'http://uri.interlex.org/base/ilx_0777082': {9, 10},
#     'http://uri.interlex.org/base/ilx_0777083': {9, 11, 12},
#     'http://uri.interlex.org/base/ilx_0777084': {8, 13, 14},
#     'http://uri.interlex.org/base/ilx_0777085': {13, 14, 15, 16, 17},
#     'http://uri.interlex.org/base/ilx_0777086': {16, 17, 18},
#     'http://uri.interlex.org/base/ilx_0777087': {17, 18},
#     'inner submucosal nerve plexus': set(range(1, 19))
# }
#
# # Build node → subtree map
# node_to_subtree = build_subtree_map(initial_tree)
#
# # Trim group entries
# trimmed_groups = trim_groups(group_dict, node_to_subtree)
#
# # Output
# print("✅ Trimmed Groups:")
# pprint(trimmed_groups)


def build_node_graph(elements):
    graph = defaultdict(lambda: {"start": [], "end": []})

    for element in elements:
        node1 = element["start_node"]
        node2 = element["end_node"]
        graph[node1]["start"].append(element["id"])
        graph[node2]["end"].append(element["id"])

    return graph


def find_neighbours(element, node_graph, node_bucket):
    node_id = element[f"{node_bucket}_node"]
    return node_graph[node_id][node_bucket]


def build_element_graph(elements, node_graph):
    element_graph = {}

    for element in elements:
        forward_neighbours = find_neighbours(element, node_graph, "start")
        backward_neighbours = find_neighbours(element, node_graph, "end")
        element_graph[element["id"]] = {
            "forward": forward_neighbours,
            "backward": backward_neighbours
        }

    return element_graph


def traverse_backwards(element_id, element_graph):
    path = [element_id]
    current_element_id = element_id

    while True:
        backward_neighbours = element_graph[current_element_id]["backward"]
        if not backward_neighbours:
            break
        current_element_id = backward_neighbours[0]  # Assuming one backward neighbour
        if current_element_id in path:
            break

        path.append(current_element_id)

    return path


def build_nested_list(node_map, start_node, node_to_element_map, visited):
    def traverse(node, is_branch=False, path=None):
        if path is None:
            path = []

        # Detect loop
        if node in path:
            return node

        path.append(node)
        visited.update(node_to_element_map.get(node, set()))

        # If no further connections, return node or list depending on context
        if node not in node_map:
            return [node] if is_branch else node

        next_nodes = node_map[node]

        # If only one path forward, continue linearly
        if len(next_nodes) == 1:
            result = traverse(next_nodes[0], path=path)
            return [node, *result] if isinstance(result, list) else [node, result]

        # If multiple paths, treat as a branch
        branch_list = [node]
        for next_node in sorted(next_nodes):
            branch_list.append(traverse(next_node, is_branch=True, path=path))
        return branch_list

    return traverse(start_node)


def _build_maps(elements):
    node_map = {}
    element_map = {}
    for element in elements:
        start= element['start_node']
        end = element['end_node']
        for node_id in [start, end]:
            if node_id not in element_map:
                element_map[node_id] = set()
            element_map[node_id].add(element['id'])

        if start not in node_map:
            node_map[start] = []
        node_map[start].append(end)

    return node_map, element_map


def find_maximal_non_branching_paths(graph):
    outgoing_edges = defaultdict(list)
    incoming_edges = defaultdict(list)
    all_nodes = set()

    for segment in graph:
        start = segment['start_node']
        end = segment['end_node']
        outgoing_edges[start].append(end)
        incoming_edges[end].append(start)
        all_nodes.add(start)
        all_nodes.add(end)

    paths = []
    visited = set()
    branching_nodes = {}

    def dfs(node_local, path):
        visited.add(node_local)
        path.append(node_local)
        if len(outgoing_edges[node_local]) != 1:
            paths.append(path[:])
            return
        for neighbor in outgoing_edges[node_local]:
            if neighbor not in visited:
                dfs(neighbor, path)
        # path.pop()

    nodes = list(outgoing_edges.keys())
    while len(nodes):
        node = nodes.pop(0)
        if node not in visited:
            dfs(node, [])

    terminal_nodes = all_nodes.difference(visited)
    for node in terminal_nodes:
        paths.append([node])

    is_tree = True
    for node in all_nodes:
        if len(outgoing_edges[node]) > 1:
            branching_nodes[node] = outgoing_edges[node]
        if len(incoming_edges[node]) > 1:
            is_tree = False
            branching_nodes[node] = list(set(branching_nodes.get(node, []) + incoming_edges[node]))

    return paths, branching_nodes, is_tree


def determine_forest(elements):
    node_graph = build_node_graph(elements)
    element_graph = build_element_graph(elements, node_graph)
    node_map, node_to_element_map = _build_maps(elements)

    all_el_ids = set(element_graph.keys())
    visited = set()

    forest = []
    forest_members = []
    remainder = all_el_ids.difference(visited)
    while remainder:
        # Select a random element.
        random_element_id = remainder.pop()

        # Traverse backwards.
        backward_path = traverse_backwards(random_element_id, element_graph)

        # Perform depth-first traversal from the starting element.
        starting_element_id = backward_path[-1]
        start_node = next(item['start_node'] for item in elements if item['id'] == starting_element_id)

        visited_before = visited.copy()

        forward_path = build_nested_list(node_map, start_node, node_to_element_map, visited)

        used_elements = visited.difference(visited_before)

        forest.append(forward_path)
        forest_members.append(used_elements)
        remainder = all_el_ids.difference(visited)

    return forest, forest_members


def is_list_of_integers(lst):
    return all(isinstance(item, int) for item in lst)


def has_subgroup_of(groups, outer_set):
    return any(val < outer_set for val in groups.values())


def get_node(nodes, node_id_map, node_id):
    return nodes[node_id_map[node_id]]


def convert_plant_to_points(plant, nodes, node_id_map, fields):
    points = [None] * len(plant)
    point_identifiers = set()
    for index, seg in enumerate(plant):
        if isinstance(seg, list):
            end_points, end_point_identifiers = convert_plant_to_points(seg, nodes, node_id_map, fields)
            point_identifiers.update(end_point_identifiers)
        else:
            end_node = get_node(nodes, node_id_map, seg)
            end_points = get_point(end_node, fields)
            point_identifiers.add(seg)

        points[index] = end_points

    return points, point_identifiers


def _match_group(target_set, labelled_sets):
    """
    Find and remove the matching labels.
    """
    matched_labels = []
    for label, id_set in list(labelled_sets.items()):
        if id_set == target_set:
            labelled_sets.pop(label)
            matched_labels.append(label)

    return matched_labels


def build_subtrees(branch, parent=None, node_to_subtree=None):
    if node_to_subtree is None:
        node_to_subtree = {}

    if isinstance(branch, list):
        for b in branch:
            build_subtrees(b, parent, node_to_subtree)
    else:
        # Leaf node
        if branch not in node_to_subtree:
            node_to_subtree[branch] = set()
        node_to_subtree[branch].add(branch)
        if parent is not None:
            if parent not in node_to_subtree:
                node_to_subtree[parent] = set()
            node_to_subtree[parent].update(node_to_subtree[branch])

    return node_to_subtree


def classify_forest(forest, plant_path_info, nodes, node_id_map, fields, group_fields):
    classification = {'contours': [], 'trees': []}
    grouped_nodes = get_group_nodes(group_fields)
    nodes_by_group = {tuple(v): k for k, v in grouped_nodes.items()}
    group_implied_structure = [set(v) for v in nodes_by_group.keys()]

    for index, plant in enumerate(forest):
        list_of_ints = is_list_of_integers(plant)
        is_contour = True if list_of_ints and not has_subgroup_of(grouped_nodes, set(plant)) else False

        if not is_contour:
            for sequence in group_implied_structure:
                plant = nest_sequence(plant, sequence)

        closed_contour = is_contour and plant[0] == plant[-1]
        if closed_contour:
            plant.pop(0)

        points, point_identifiers = convert_plant_to_points(plant, nodes, node_id_map, fields)
        if closed_contour:
            # I think this will be okay for closed contours because the point_identifiers
            # will still match when start point is added back in later.
            # point_identifiers is a set and I don't know which identifier corresponds to
            # the last point in the list of points.
            points.pop()

        start_node = get_node(nodes, node_id_map,  plant[0])

        metadata = {}
        if closed_contour:
            metadata["closed"] = True

        print(point_identifiers)
        print(duplicate_structure(plant))
        matching_labels = _match_group(point_identifiers, grouped_nodes)
        # for gg in grouped_nodes.values():
        #     print(gg, gg < set(point_identifiers))

        colour = get_colour(start_node, fields)
        metadata["colour"] = colour
        metadata['labels'] = matching_labels
        resolution = get_resolution(start_node, fields)
        if resolution is not None:
            metadata['resolution'] = resolution

        category = 'contours' if is_contour else 'trees'
        classification[category].append({"points": points, "metadata": [metadata]})

    return classification

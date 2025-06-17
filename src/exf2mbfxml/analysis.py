from cmlibs.zinc.context import Context

from exf2mbfxml.utilities import nest_sequence, get_unique_list_paths, get_identifiers_from_path, determine_fields
from exf2mbfxml.zinc import get_point, get_colour, get_resolution, get_markers, get_string

from typing import Union, List
from collections import defaultdict

Branch = Union[int, List["Branch"]]


def _build_node_graph(elements):
    graph = defaultdict(lambda: {"start": [], "end": []})

    for element in elements:
        node1 = element["start_node"]
        node2 = element["end_node"]
        graph[node1]["start"].append(element["id"])
        graph[node2]["end"].append(element["id"])

    return graph


def _find_neighbours(element, node_graph, buckets):
    node_id = element[buckets[0]]
    return node_graph[node_id][buckets[1]]


def _build_element_graph(elements, node_graph):
    element_graph = {}

    for element in elements:
        forward_neighbours = _find_neighbours(element, node_graph, ["end_node", "start"])
        backward_neighbours = _find_neighbours(element, node_graph, ["start_node", "end"])
        element_graph[element["id"]] = {
            "forward": forward_neighbours,
            "backward": backward_neighbours
        }

    return element_graph


def _traverse_backwards(element_id, element_graph):
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


def _traverse_forward_path(node_map, start_node, node_to_element_map, visited):
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
    node_map = defaultdict(list)
    reverse_node_map = defaultdict(list)
    element_map = defaultdict(set)
    for element in elements:
        start = element['start_node']
        end = element['end_node']
        element_map[start].add(element['id'])
        element_map[end].add(element['id'])
        node_map[start].append(end)
        reverse_node_map[end].append(start)

    return node_map, reverse_node_map, element_map


def _flatten_to_set(nested_list):
    flat_set = set()

    def flatten(item):
        if isinstance(item, list):
            for sub_item in item:
                flatten(sub_item)
        else:
            flat_set.add(item)

    flatten(nested_list)
    return flat_set


def _find_edges(forward_map, reverse_map):
    edges = []

    def is_junction(node):
        return len(forward_map.get(node, [])) > 1 or len(reverse_map.get(node, [])) > 1

    def traverse_edge(start_node, seeded_next_node):
        edge = [start_node]
        current_node = start_node
        while len(forward_map.get(current_node, [])) > 0:
            next_node = forward_map[current_node][0] if seeded_next_node is None else seeded_next_node
            seeded_next_node = None
            edge.append(next_node)
            if is_junction(next_node):
                break
            current_node = next_node
        edges.append(edge)

    # Find start points (nodes with no incoming edges or junctions).
    start_points = set(forward_map.keys()) - set(reverse_map.keys())
    junctions = {node for node in forward_map if is_junction(node)}

    for start_point in start_points.union(junctions):
        for out_node in forward_map[start_point]:
            traverse_edge(start_point, out_node)

    return tuple(edges)


def determine_forest(elements, grouped_identifiers):
    node_graph = _build_node_graph(elements)
    element_graph = _build_element_graph(elements, node_graph)
    node_map, reverse_node_map, node_to_element_map = _build_maps(elements)

    all_el_ids = set(element_graph.keys())
    visited = set()

    element_lookup = {el['id']: el for el in elements}

    group_start_nodes = set()
    for group in grouped_identifiers.values():

        element_ids = group.get('elements', [])
        try:
            element_id = element_ids.pop()
            element_ids.add(element_id)
        except KeyError:
            continue

        sub_element_graph = {e: {'backward': list(set(v['backward']).intersection(element_ids))} for e, v in element_graph.items() if e in element_ids}
        backward_path = _traverse_backwards(element_id, sub_element_graph)
        start_node = _find_node_at(backward_path, element_lookup, 'start')
        end_node = _find_node_at(backward_path, element_lookup, 'end')
        group_start_nodes.add((start_node, end_node))

    forest = []
    remainder = all_el_ids.difference(visited)
    while remainder:
        # Select a random element.
        random_element_id = remainder.pop()

        # Traverse backwards.
        backward_path = _traverse_backwards(random_element_id, element_graph)

        # Perform depth-first traversal from the starting element.
        start_node = _find_node_at(backward_path, element_lookup, 'start')

        forward_path = _traverse_forward_path(node_map, start_node, node_to_element_map, visited)
        path_nodes = _flatten_to_set(forward_path)
        if _is_vessel_path(path_nodes, reverse_node_map):
            filtered_node_map = {}
            for node_id in path_nodes:
                if node_id in node_map:
                    filtered_node_map[node_id] = node_map[node_id]
            forward_path = _find_edges(filtered_node_map, reverse_node_map)

        forest.append(forward_path)
        remainder = all_el_ids.difference(visited)

    return forest, group_start_nodes


def _find_node_at(backward_path, element_lookup, location):
    starting_element_id = backward_path[-1]
    starting_element = element_lookup[starting_element_id]
    return starting_element[f'{location}_node']


def _is_vessel_path(path_nodes, reverse_node_map):
    for node_id in path_nodes:
        if len(reverse_node_map.get(node_id, [])) > 1:
            return True

    return False


def _is_list_of_integers(lst):
    return all(isinstance(item, int) for item in lst)


def _has_subgroup_of(groups, outer_set):
    return any(val < outer_set for val in groups.values() if val)


def _get_node(nodes, node_id_map, node_id):
    return nodes[node_id_map[node_id]]


def _convert_plant_to_points(plant, nodes, node_id_map, fields):
    points = [None] * len(plant)
    point_identifiers = set()
    for index, seg in enumerate(plant):
        if isinstance(seg, list):
            end_points, end_point_identifiers = _convert_plant_to_points(seg, nodes, node_id_map, fields)
            point_identifiers.update(end_point_identifiers)
        else:
            end_node = _get_node(nodes, node_id_map, seg)
            end_points = get_point(end_node, fields)
            point_identifiers.add(seg)

        points[index] = end_points

    return points, point_identifiers


def _condition_equal(set_a, set_b):
    return set_a == set_b


def _condition_lt(set_a, set_b):
    return set_a < set_b


def _match_group(target_set, labelled_sets, destructively=True, condition_fcn=None):
    """
    Find and remove the matching labels.
    Matched labels are removed from the labelled sets input dictionary.
    """
    if condition_fcn is None:
        condition_fcn = _condition_equal
    matched_labels = []
    for label, id_set in list(labelled_sets.items()):
        if condition_fcn(target_set, id_set):
            matched_labels.append(label)
            if destructively:
                labelled_sets.pop(label)

    return matched_labels


def _update_grouped_nodes(grouped_nodes, group_start_nodes, plant_set):
    used_tuples = set()

    modified = False
    for start_node in group_start_nodes:
        first, second = start_node
        for key, node_set in grouped_nodes.items():
            if first in node_set and second in node_set and node_set < plant_set:
                node_set.discard(first)
                used_tuples.add(start_node)
                modified = True

    # Remove used tuples from group_start_nodes
    group_start_nodes -= used_tuples

    return modified


def classify_forest(forest, nodes, node_id_map, fields, grouped_nodes, group_start_nodes):
    classification = {'contours': [], 'trees': [], 'vessels': []}
    group_implied_structure = _update_node_groups(grouped_nodes)

    for index, plant in enumerate(forest):
        is_vessel = isinstance(plant, tuple)
        list_of_ints = _is_list_of_integers(plant)
        is_contour = True if not is_vessel and list_of_ints and not _has_subgroup_of(grouped_nodes, set(plant)) else False
        is_tree = not is_vessel and not is_contour

        remove_start_nodes = None
        for start_nodes in group_start_nodes:
            if plant[0] == start_nodes[0] and len(plant) > 1 and plant[1] == start_nodes[1]:
                remove_start_nodes = start_nodes
                break

        if remove_start_nodes is not None:
            group_start_nodes.remove(remove_start_nodes)

        if is_tree:
            if group_start_nodes:
                plant_set = _flatten_to_set(plant)
                modification_made = _update_grouped_nodes(grouped_nodes, group_start_nodes, plant_set)
                if modification_made:
                    group_implied_structure = _update_node_groups(grouped_nodes)

            for sequence in group_implied_structure:
                plant = nest_sequence(plant, sequence)

        closed_contour = is_contour and plant[0] == plant[-1]
        if closed_contour:
            plant.pop()

        points, point_identifiers = _convert_plant_to_points(plant, nodes, node_id_map, fields)

        start_node_id = plant[0][0] if is_vessel else plant[0]
        start_node = _get_node(nodes, node_id_map, start_node_id)
        matching_global_labels = _match_group(point_identifiers, grouped_nodes)
        matching_global_labels.extend(_match_group(point_identifiers, grouped_nodes, destructively=False, condition_fcn=_condition_lt))

        colour = get_colour(start_node, fields)
        metadata = {'global': {'labels': matching_global_labels, 'colour': colour}}
        if closed_contour:
            metadata['global']['closed'] = True
        resolution = get_resolution(start_node, fields)
        if resolution is not None:
            metadata['global']['resolution'] = resolution

        if is_tree:
            unique_paths = get_unique_list_paths(plant)
            indexed_metadata = {}
            for u in unique_paths:
                path_identifiers = set(get_identifiers_from_path(u, plant))
                matched_groups = _match_group(path_identifiers, grouped_nodes)
                matched_groups.extend(_match_group(path_identifiers, grouped_nodes, destructively=False, condition_fcn=_condition_lt))
                matched_groups = set(matched_groups).difference(set(matching_global_labels))
                indexed_metadata[u] = list(matched_groups)
            metadata['indexed'] = indexed_metadata

        category = 'contours' if is_contour else 'trees' if is_tree else 'vessels'
        classification[category].append({"points": points, "metadata": metadata})

    return classification


def _update_node_groups(grouped_nodes):
    nodes_by_group = {tuple(v): k for k, v in grouped_nodes.items()}
    group_implied_structure = [set(v) for v in nodes_by_group.keys() if v]
    return group_implied_structure


def read_markers(region, fields):
    datapoints = get_markers(region)
    return [{"point": get_point(datapoint, fields), "metadata": {"name": get_string(datapoint, "marker_name"), "colour": get_colour(datapoint, fields)}} for datapoint in datapoints]


def is_suitable_mesh(input_argument):
    """
    Test if the given mesh is suitable for extracting into MBF XML format.
    The input can either be a string specifying an EXF file location, or a Zinc Region.
    """
    if isinstance(input_argument, str):
        context = Context("valid")
        region = context.getDefaultRegion()
        region.readFile(input_argument)
    else:
        region = input_argument

    field_module = region.getFieldmodule()
    coordinates_field, available_fields, group_fields = determine_fields(field_module)

    mesh_1d = field_module.findMeshByDimension(1)

    element_iterator = mesh_1d.createElementiterator()
    element = element_iterator.next()
    while element.isValid():
        eft = element.getElementfieldtemplate(coordinates_field, -1)
        local_nodes_count = eft.getNumberOfLocalNodes()
        if local_nodes_count != 2:
            return False

        for node_index in [1, 2]:
            node = element.getNode(eft, node_index)
            node_identifier = node.getIdentifier()
            if node_identifier == -1:
                return False

        element = element_iterator.next()

    return True

from collections import defaultdict

from exf2mbfxml.zinc import get_point, get_colour, get_resolution, get_group_nodes


def build_node_graph(elements):
    graph = defaultdict(lambda: {"start": [], "end": []})

    for element in elements:
        node1, node2 = element["nodes"]
        graph[node1]["start"].append(element["id"])
        graph[node2]["end"].append(element["id"])

    return graph


def find_neighbours(element, node_graph, node_index, node_bucket):
    node_id = element["nodes"][node_index]
    return node_graph[node_id][node_bucket]


def build_element_graph(elements, node_graph):
    element_graph = {}

    for element in elements:
        forward_neighbours = find_neighbours(element, node_graph, 1, "start")
        backward_neighbours = find_neighbours(element, node_graph, 0, "end")
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


def depth_first_traversal(element_id, element_graph, visited):
    path = []
    stack = [(element_id, [])]

    while stack:
        current_element_id, sub_path = stack.pop()
        loop_detected = current_element_id in path
        path.append(current_element_id)
        visited.add(current_element_id)
        if loop_detected:
            break

        forward_neighbours = element_graph[current_element_id]["forward"]
        if forward_neighbours:
            forward_neighbours.sort(reverse=True)  # Sort to prioritize the highest identifier
            while len(forward_neighbours) > 1:
                child_element_id = forward_neighbours.pop(0)
                path.append(depth_first_traversal(child_element_id, element_graph, visited))

            stack.append((forward_neighbours[0], sub_path))

    return path


def determine_forest(elements):
    node_graph = build_node_graph(elements)
    element_graph = build_element_graph(elements, node_graph)

    all_el_ids = set(element_graph.keys())
    visited = set()

    forest = []
    remainder = all_el_ids.difference(visited)
    while remainder:
        # Select a random element.
        random_element_id = remainder.pop()

        # Traverse backwards.
        backward_path = traverse_backwards(random_element_id, element_graph)

        # Perform depth-first traversal from the starting element.
        starting_element_id = backward_path[-1]
        forward_path = depth_first_traversal(starting_element_id, element_graph, visited)
        forest.append(forward_path)
        remainder = all_el_ids.difference(visited)

    return forest


def is_list_of_integers(lst):
    return all(isinstance(item, int) for item in lst)


def get_node(element, nodes, node_id_map, index):
    end_node_id = element["nodes"][index]
    return nodes[node_id_map[end_node_id]], end_node_id


def convert_tree_to_points(tree, elements, element_id_map, nodes, node_id_map, fields):
    points = [None] * len(tree)
    point_identifiers = set()
    for index, seg in enumerate(tree):
        if isinstance(seg, list):
            end_points, end_point_identifiers = convert_tree_to_points(seg, elements, element_id_map, nodes, node_id_map, fields)
        else:
            end_node, end_point_identifiers = get_node(elements[element_id_map[seg]], nodes, node_id_map, 1)
            end_points = get_point(end_node, fields)

        points[index] = end_points
        point_identifiers.add(end_point_identifiers)

    return points, point_identifiers


def _match_group(target_set, labelled_sets):
    # Find and remove the matching labels
    matched_labels = []
    for label, id_set in list(labelled_sets.items()):
        if id_set == target_set:
            labelled_sets.pop(label)
            matched_labels.append(label)

    return matched_labels


def classify_forest(forest, elements, element_id_map, nodes, node_id_map, fields, group_fields):
    classification = {'contours': [], 'trees': []}
    grouped_nodes = get_group_nodes(group_fields)
    for index, plant in enumerate(forest):
        is_contour = is_list_of_integers(plant)
        closed_contour = is_contour and plant[0] == plant[-1]
        if closed_contour:
            plant.pop(0)

        points, point_identifiers = convert_tree_to_points(plant, elements, element_id_map, nodes, node_id_map, fields)
        if closed_contour:
            # I think this will be okay for closed contours because the point_identifiers
            # will still match when start point is added back in later.
            points.pop()

        start_node, start_node_id = get_node(elements[element_id_map[plant[0]]], nodes, node_id_map, 0)
        start_point = get_point(start_node, fields)
        point_identifiers.add(start_node_id)

        metadata = {}
        if closed_contour:
            metadata["closed"] = True

        matching_labels = _match_group(point_identifiers, grouped_nodes)

        colour = get_colour(start_node, fields)
        metadata["colour"] = colour
        metadata['labels'] = matching_labels
        resolution = get_resolution(start_node, fields)
        if resolution is not None:
            metadata['resolution'] = resolution

        category = 'contours' if is_contour else 'trees'
        classification[category].append({"points": [start_point, *points], "metadata": [metadata]})

    return classification

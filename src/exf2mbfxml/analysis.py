from collections import defaultdict


def build_node_graph(elements):
    graph = defaultdict(lambda: {'start': [], 'end': []})

    for element in elements:
        node1, node2 = element.nodes
        graph[node1.id]['start'].append(element.id)
        graph[node2.id]['end'].append(element.id)

    return graph


def find_neighbours(element, node_graph, node_index, node_bucket):
    node_id = element.nodes[node_index].id
    return node_graph[node_id][node_bucket]


def build_element_graph(elements, node_graph):
    element_graph = {}

    for element in elements:
        forward_neighbours = find_neighbours(element, node_graph, 1, 'start')
        backward_neighbours = find_neighbours(element, node_graph, 0, 'end')
        element_graph[element.id] = {
            'forward': forward_neighbours,
            'backward': backward_neighbours
        }

    return element_graph


def traverse_backwards(element_id, element_graph):
    path = [element_id]
    current_element_id = element_id

    while True:
        backward_neighbours = element_graph[current_element_id]['backward']
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

        forward_neighbours = element_graph[current_element_id]['forward']
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
        # Select a random element
        random_element_id = remainder.pop()

        # Traverse backwards
        backward_path = traverse_backwards(random_element_id, element_graph)

        # Perform depth-first traversal from the starting element
        starting_element_id = backward_path[-1]
        forward_path = depth_first_traversal(starting_element_id, element_graph, visited)
        forest.append(forward_path)
        remainder = all_el_ids.difference(visited)

    return forest


def is_list_of_integers(lst):
    return all(isinstance(item, int) for item in lst)


def convert_tree_to_points(tree, elements, element_id_map):
    points = [None] * len(tree)
    for index, seg in enumerate(tree):
        if isinstance(seg, list):
            end_points = convert_tree_to_points(seg, elements)
        else:
            end_points = elements[element_id_map[seg]].end_point()

        points[index] = end_points

    return points


def classify_forest(forest, elements, element_id_map):
    tree_is_contour = [None] * len(forest)
    leaved_trees = []
    tree_annotations = []
    for index, tree in enumerate(forest):
        is_contour = is_list_of_integers(tree)
        closed_contour = is_contour and tree[0] == tree[-1]
        if closed_contour:
            tree.pop()

        points = convert_tree_to_points(tree, elements, element_id_map)
        metadata = {}
        if closed_contour:
            metadata["closed"] = True
        start_point = elements[element_id_map[tree[0]]].start_point()
        leaved_trees.append([start_point, *points])
        tree_annotations.append(metadata)
        tree_is_contour[index] = is_contour

    # classification = {"contours": {"points": [], "metadata": None}, "trees": {"points": [], "metadata": None}}
    category = "contours" if all(tree_is_contour) else "trees"
    classification = {category: {}}
    classification[category]["points"] = leaved_trees
    classification[category]["metadata"] = tree_annotations

    return classification

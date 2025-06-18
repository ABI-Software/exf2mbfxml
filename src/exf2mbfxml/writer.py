import xml.etree.ElementTree as ET
from exf2mbfxml import __version__ as package_version
from exf2mbfxml.utilities import is_valid_xml


def _is_trace_association(label):
    return label.startswith('http://') or label.startswith('https://')


def _write_contour(contour, parent_element):
    points = contour.get("points", [])
    metadata = contour.get("metadata", [])
    if not points:
        return

    current_metadata = metadata['global']
    top_level = parent_element.tag == 'mbf'
    labels = current_metadata.get('labels', [])
    attributes = {'colour': current_metadata.get('colour', '#000000'), 'shape': 'Contour'}
    closed_contour = current_metadata.get('closed', None)
    if closed_contour is not None:
        attributes['closed'] = str(closed_contour).lower()

    if labels:
        filtered = [s for s in labels if not _is_trace_association(s)]
        if filtered:
            shortest = min(filtered, key=len)
            labels.remove(shortest)
            attributes['name'] = shortest

    # Create the contour element
    contour_element = ET.SubElement(parent_element, "contour", attributes)

    # Add properties
    global_uid = current_metadata.get('GUID', '')
    if global_uid:
        guid_element = ET.SubElement(contour_element, "property", name="GUID")
        ET.SubElement(guid_element, "s").text = global_uid

    fill_density = current_metadata.get('FillDensity', False)
    if fill_density:
        fill_density_element = ET.SubElement(contour_element, "property", name="FillDensity")
        ET.SubElement(fill_density_element, "n").text = str(fill_density)

    resolution = current_metadata.get('resolution', None)
    if resolution is not None:
        ET.SubElement(contour_element, "resolution").text = str(resolution)

    _define_properties(contour_element, labels)

    # Add points
    for point in points:
        _write_point(contour_element, point)


def _define_properties(parent_element, labels):
    """
    Only useful for setting single string properties.
    Will differentiate between trace association and non-trace associations
    using a very basic heuristic.
    """
    for label in labels:
        tag_name = 'Set'
        if _is_trace_association(label):
            tag_name = 'TraceAssociation'
        elif is_valid_xml(label):
            tag_name = None
            child = ET.fromstring(label)
            parent_element.append(child)

        if tag_name is not None:
            set_property_element = ET.SubElement(parent_element, 'property', name=tag_name)
            ET.SubElement(set_property_element, 's').text = label


def _write_point(parent_element, point):
    ET.SubElement(parent_element, "point", x=f'{point[0]:.2f}', y=f'{point[1]:.2f}', z=f'{point[2]:.2f}', d=f'{point[3]:.2f}')


def _write_branch(parent_element, tag, attributes, points, path, indexed_labels):
    branch_element = ET.SubElement(parent_element, tag, attrib=attributes)

    current_label_path = tuple(path + [0])
    _define_properties(branch_element, indexed_labels.get(current_label_path, []))

    for i, point in enumerate(points):
        current_path = path + [i]

        if isinstance(point[0], float):
            _write_point(branch_element, point)
        else:
            child_label_path = tuple(current_path + [0])
            branch_labels = indexed_labels.get(child_label_path, [])
            branch_class = _extract_branch_class(branch_labels)

            if branch_class:
                indexed_labels[child_label_path].remove(branch_class)
                branch_attributes = {'class': branch_class}
            else:
                branch_attributes = {}

            _write_branch(branch_element, "branch", branch_attributes, point, current_path, indexed_labels)


def _extract_branch_class(labels):
    """Extract the first label that is not a trace association or valid XML."""
    for label in labels:
        if not _is_trace_association(label) and not is_valid_xml(label):
            return label
    return None


def _write_tree(tree, parent_element):
    points = tree.get("points", [])
    metadata = tree.get("metadata", [])
    if not points:
        return

    top_level = parent_element.tag == 'mbf'

    global_labels = metadata['global'].get('labels', [])
    indexed_labels = metadata['indexed']

    TREE_TYPES = ['Dendrite']

    attributes = {'color': metadata['global'].get('colour', '#000000')}
    if global_labels:
        filtered = [s for s in global_labels if not _is_trace_association(s) and not is_valid_xml(s)]
        for item in filtered:
            if item in TREE_TYPES:
                attributes['type'] = item
            else:
                attributes['rootclass'] = item

    _write_branch(parent_element, "tree", attributes, points, [], indexed_labels)


def _write_vessel(vessel, parent_element):
    points = vessel.get("points", [])
    metadata = vessel.get("metadata", [])
    if not points:
        return

    top_level = parent_element.tag == 'mbf'

    attributes = {'color': metadata['global'].get('colour', '#000000'), 'version': '4'}
    global_labels = metadata['global'].get('labels', [])
    if global_labels:
        filtered = [s for s in global_labels if not _is_trace_association(s)]
        for item in filtered:
            attributes['class'] = item

    vessel_element = ET.SubElement(parent_element, 'vessel', attrib=attributes)
    nodes_element = ET.SubElement(vessel_element, "nodes")
    edges_element = ET.SubElement(vessel_element, "edges")
    edgelists_element = ET.SubElement(vessel_element, "edgelists")

    node_id_map = {}
    node_id_counter = 0
    edge_id_counter = 0

    def add_node(pt):
        nonlocal node_id_counter
        point_tuple = tuple(pt[:4])
        if point_tuple not in node_id_map:
            node = ET.SubElement(nodes_element, "node", id=str(node_id_counter))
            _write_point(node, pt)
            # ET.SubElement(node, "point", x=str(pt[0]), y=str(pt[1]), z=str(pt[2]), d=str(pt[3]))
            node_id_map[point_tuple] = node_id_counter
            node_id_counter += 1
        return node_id_map[point_tuple]

    for edge in points:
        edge_element = ET.SubElement(edges_element, "edge", id=str(edge_id_counter))
        for point in edge:
            _write_point(edge_element, point)
            # ET.SubElement(edge_element, "point", x=str(point[0]), y=str(point[1]), z=str(point[2]), d=str(point[3]))

        source_node_id = add_node(edge[0])
        target_node_id = add_node(edge[-1])

        ET.SubElement(edgelists_element, "edgelist", id=str(edge_id_counter), edge=str(edge_id_counter), sourcenode=str(source_node_id), targetnode=str(target_node_id))

        edge_id_counter += 1


def _write_marker(marker, root):
    point = marker.get("point", [])
    metadata = marker.get("metadata", [])
    if not point:
        return

    attributes = {'color': metadata.get('colour', '#000000'), 'name': metadata.get('name', '')}
    marker_element = ET.SubElement(root, 'marker', attrib=attributes)
    _write_point(marker_element, point)


def write_mbfxml(output_mbf, data, options=None):
    # Create the root element
    root = ET.Element("mbf", version="4.0", xmlns="http://www.mbfbioscience.com/2007/neurolucida",
                      appname="Exf2MBFXML", appversion=package_version)

    for marker in data.get('markers', []):
        _write_marker(marker, root)

    for contour in data.get('contours', []):
        _write_contour(contour, root)

    for tree in data.get('trees', []):
        _write_tree(tree, root)

    for vessel in data.get('vessels', []):
        _write_vessel(vessel, root)

    # Create the XML tree and write to a file
    tree = ET.ElementTree(root)
    ET.indent(tree, level=0)
    tree.write(output_mbf, encoding="ISO-8859-1", xml_declaration=True)

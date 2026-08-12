import os

from cmlibs.utils.zinc.finiteelement import create_element_from_node_identifiers
from cmlibs.utils.zinc.general import ChangeManager, AbstractNodeDataObject, create_node
from cmlibs.zinc.context import Context
from cmlibs.zinc.field import FieldFindMeshLocation, Field
from cmlibs.zinc.result import RESULT_OK

from exf2mbfxml.analysis import determine_forest, classify_forest, read_markers
from exf2mbfxml.exceptions import EXFFile
from exf2mbfxml.utilities import determine_fields
from exf2mbfxml.zinc import get_group_elements_and_nodes


def read_exf(file_name):
    if os.path.exists(file_name):
        context = Context("read")
        region = context.createRegion()
        result = region.readFile(file_name)
        if result != RESULT_OK:
            return None

        return extract_mesh_info(region)

    raise EXFFile(f'File does not exist: "{file_name}"')


def extract_mesh_info(region):
    field_module = region.getFieldmodule()
    mesh_1d = field_module.findMeshByDimension(1)
    analysis_elements = [None] * mesh_1d.getSize()
    element_iterator = mesh_1d.createElementiterator()
    element = element_iterator.next()
    if not element.isValid():
        return None

    index = 0
    coordinates_field, available_fields, group_fields = determine_fields(field_module)
    data_fields = {available_field.getName(): available_field for available_field in available_fields}
    grouped_identifiers = get_group_elements_and_nodes(group_fields)

    # _print_check_on_field_names(available_fields)

    node_element_map = {}
    element_identifier_to_index_map = {}
    invalid_element_identifiers = []
    nodes = []
    node_identifier_to_index_map = {}
    visited_elements = set()
    while element.isValid():
        element_identifier = element.getIdentifier()
        visited_elements.add(element_identifier)
        eft = element.getElementfieldtemplate(coordinates_field, -1)
        if eft.isValid():
            local_nodes_count = eft.getNumberOfLocalNodes()
            if local_nodes_count == 2:
                visited_elements.remove(element_identifier)
                local_node_identifiers = []
                for i in range(local_nodes_count):
                    node = element.getNode(eft, i + 1)
                    node_identifier = node.getIdentifier()
                    if node_identifier not in node_identifier_to_index_map:
                        node_identifier_to_index_map[node_identifier] = len(nodes)
                        nodes.append(node)

                    local_node_identifiers.append(node_identifier)
                node_element_map[tuple(local_node_identifiers)] = element_identifier
                analysis_elements[index] = {'id': element_identifier, 'start_node': local_node_identifiers[0], 'end_node': local_node_identifiers[1]}
                element_identifier_to_index_map[element_identifier] = index
            elif local_nodes_count == 3:
                coordinates = _evaluate_field_data(element, 0.0, coordinates_field)
                local_nodes_count = eft.getNumberOfLocalNodes()
                local_node_identifiers = []
                for i in range(local_nodes_count):
                    node = element.getNode(eft, i + 1)

                    node_identifier = node.getIdentifier()
                    if node_identifier not in node_identifier_to_index_map:
                        node_identifier_to_index_map[node_identifier] = len(nodes)
                        nodes.append(node)

                    local_node_identifiers.append(node_identifier)

                node_element_key = tuple(local_node_identifiers[:2])
                source_element_identifier = node_element_map.get(node_element_key, node_element_key)
                analysis_elements[index] = {'id': element_identifier, 'branch_element': source_element_identifier, 'coordinates': coordinates, 'end_node': local_node_identifiers[2],}
            else:
                print(f'Invalid number of local nodes: {eft.getNumberOfLocalNodes()}')
        else:
            invalid_element_identifiers.append(element_identifier)

        element = element_iterator.next()
        index += 1

    # Clean up analysis elements.
    analysis_elements = [item for item in analysis_elements if item is not None]

    # Find branching points for 3 node elements.
    replaced_elements = {}
    branches = {}
    with ChangeManager(field_module):
        mesh_cache = field_module.createFieldcache()
        find_mesh_location = field_module.createFieldFindMeshLocation(coordinates_field, coordinates_field, mesh_1d)
        find_mesh_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_NEAREST)
        field_group = field_module.createFieldGroup()
        mesh_group = field_group.getOrCreateMeshGroup(mesh_1d)

        for index, item in enumerate(analysis_elements):
            if 'branch_element' in item:
                branch_element = node_element_map[item['branch_element']] if isinstance(item['branch_element'], tuple) else item['branch_element']
                element = mesh_1d.findElementByIdentifier(branch_element)
                mesh_group.addElement(element)
                find_mesh_location.setSearchMesh(mesh_group)

                mesh_cache.setFieldReal(coordinates_field, item['coordinates'])
                search_element, xi = find_mesh_location.evaluateMeshLocation(mesh_cache, 1)
                # print('answer:', search_element.getIdentifier(), element.getIdentifier(), xi)
                item['branch_location'] = xi
                mesh_group.removeElement(element)
                branches.setdefault(branch_element, []).append((xi, item['coordinates'], item['end_node'], item['id']))
                replaced_elements[item['id']] = set()

    # Replace virtual nodes with physical nodes and adjust the element into line segments
    # that connects the branch nodes into the original element.
    remove_indices = []
    node_set = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_data = AbstractNodeDataObject([coordinates_field.getName()])
    for branch_element, xi_list in branches.items():
        sorted_xi_list = sorted(xi_list, key=lambda x: x[0])
        index = 0
        replace_index = element_identifier_to_index_map[branch_element]
        remove_indices.append(replace_index)
        replaced_elements[branch_element] = set()
        start_node = analysis_elements[replace_index]['start_node']
        final_end_node = analysis_elements[replace_index]['end_node']
        for xi, coordinates, end_node, identifier in sorted_xi_list:
            current_coordinates = coordinates
            setattr(node_data, coordinates_field.getName(), lambda: current_coordinates)
            node_identifier = create_node(field_module, node_data)
            if node_identifier not in node_identifier_to_index_map:
                node_identifier_to_index_map[node_identifier] = len(nodes)
                node = node_set.findNodeByIdentifier(node_identifier)
                nodes.append(node)
            index += 1

            # Create the connecting element from the start node to the new branch node.
            element_identifier = create_element_from_node_identifiers(mesh_1d, coordinates_field, [start_node, node_identifier])
            analysis_elements.append({'id': element_identifier, 'start_node': start_node, 'end_node': node_identifier})
            replaced_elements[branch_element].add(element_identifier)

            # Create the branch element.
            element_identifier = create_element_from_node_identifiers(mesh_1d, coordinates_field, [node_identifier, end_node])
            analysis_elements.append({'id': element_identifier, 'start_node': node_identifier, 'end_node': end_node})
            start_node = node_identifier
            replaced_elements[identifier].add(element_identifier)

        # Create the connecting element from the branch node to the end of the original element.
        element_identifier = create_element_from_node_identifiers(mesh_1d, coordinates_field, [start_node, final_end_node])
        analysis_elements.append({'id': element_identifier, 'start_node': start_node, 'end_node': final_end_node})
        replaced_elements[branch_element].add(element_identifier)

    for index in reversed(sorted(remove_indices)):
        del analysis_elements[index]

    # Filter out all the replaced branch elements.
    analysis_elements = [item for item in analysis_elements if 'branch_element' not in item]

    # Re-create element_identifier_to_index_map = {}
    element_identifier_to_index_map = {item['id']: index for index, item in enumerate(analysis_elements)}

    # Clean up group_identifiers
    for group in grouped_identifiers:
        grouped_identifiers[group]['elements'] -= set(invalid_element_identifiers)
        for key, value in replaced_elements.items():
            if key in grouped_identifiers[group]['elements']:
                grouped_identifiers[group]['elements'].remove(key)
                grouped_identifiers[group]['elements'].update(value)

        grouped_identifiers[group]['nodes'] = set()
        for element_identifier in grouped_identifiers[group]['elements']:
            index = element_identifier_to_index_map[element_identifier]
            analysis_element = analysis_elements[index]
            grouped_identifiers[group]['nodes'].add(analysis_element['start_node'])
            grouped_identifiers[group]['nodes'].add(analysis_element['end_node'])

    forest, group_start_nodes = determine_forest(analysis_elements, grouped_identifiers)

    grouped_nodes = {k: v['nodes'] for k, v in grouped_identifiers.items()}
    mesh_info = classify_forest(forest, nodes, node_identifier_to_index_map, data_fields, grouped_nodes, group_start_nodes)

    mesh_info['markers'] = read_markers(region, data_fields)
    return mesh_info


def _print_check_on_field_names(available_fields):  # pragma: no cover
    print('Check field name for internal fields.')
    CHECKED_FIELD_NAMES = ['coordinates', 'radius', 'rgb']
    for a in available_fields:
        if a.getName() not in CHECKED_FIELD_NAMES:
            print(a.getName())
    print('Check complete.')


def _evaluate_field_data(element, xi, data_field):
    mesh = element.getMesh()
    fm = mesh.getFieldmodule()
    fc = fm.createFieldcache()

    components_count = data_field.getNumberOfComponents()

    fc.setMeshLocation(element, xi)
    result, values = data_field.evaluateReal(fc, components_count)
    if result == RESULT_OK:
        return values

    return None

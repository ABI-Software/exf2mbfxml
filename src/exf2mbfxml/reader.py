import os

from cmlibs.zinc.context import Context
from cmlibs.zinc.result import RESULT_OK

from exf2mbfxml.analysis import determine_forest, classify_forest, read_markers
from exf2mbfxml.exceptions import EXFFile
from exf2mbfxml.utilities import determine_fields
from exf2mbfxml.zinc import get_group_nodes, get_group_elements_and_nodes


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
    mesh_info = {}
    field_module = region.getFieldmodule()
    mesh_1d = field_module.findMeshByDimension(1)
    analysis_elements = [None] * mesh_1d.getSize()
    element_iterator = mesh_1d.createElementiterator()
    element = element_iterator.next()
    index = 0
    coordinates_field, available_fields, group_fields = determine_fields(field_module)
    data_fields = {available_field.getName(): available_field for available_field in available_fields}
    grouped_identifiers = get_group_elements_and_nodes(group_fields)

    # _print_check_on_field_names(available_fields)

    # Assumes all elements define the same element field template.
    eft = element.getElementfieldtemplate(coordinates_field, -1)
    local_nodes_count = eft.getNumberOfLocalNodes()
    if local_nodes_count == 2:
        element_identifier_to_index_map = {}
        nodes = []
        node_identifier_to_index_map = {}
        while element.isValid():
            element_identifier = element.getIdentifier()
            eft = element.getElementfieldtemplate(coordinates_field, -1)
            local_node_identifiers = []
            for i in range(local_nodes_count):
                node = element.getNode(eft, i + 1)
                node_identifier = node.getIdentifier()
                if node_identifier not in node_identifier_to_index_map:
                    node_identifier_to_index_map[node_identifier] = len(nodes)
                    nodes.append(node)

                local_node_identifiers.append(node_identifier)
            # Element(element_identifier, local_node_identifiers[0], local_node_identifiers[1])
            analysis_elements[index] = {'id': element_identifier, 'start_node': local_node_identifiers[0], 'end_node': local_node_identifiers[1]}
            element_identifier_to_index_map[element_identifier] = index
            element = element_iterator.next()
            index += 1

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

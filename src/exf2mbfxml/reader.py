import os

from cmlibs.utils.zinc.field import field_is_managed_coordinates
from cmlibs.zinc.context import Context
from cmlibs.zinc.result import RESULT_OK

from exf2mbfxml.analysis import determine_forest, classify_forest
from exf2mbfxml.exceptions import EXFFile


def read_exf(file_name):
    if os.path.exists(file_name):
        context = Context("read")
        region = context.createRegion()
        result = region.readFile(file_name)
        if result != RESULT_OK:
            return None

        return extract_mesh_info(region)

    raise EXFFile(f'File does not exist: "{file_name}"')


def _find_likely_coordinate_field(field_module):
    field_iterator = field_module.createFielditerator()
    field = field_iterator.next()
    likely_coordinates_field = None
    candidate_coordinate_field = None
    while field.isValid() and likely_coordinates_field is None:
        if field_is_managed_coordinates(field):
            candidate_coordinate_field = field

        if candidate_coordinate_field is not None and candidate_coordinate_field.getName() == 'coordinates':
            likely_coordinates_field = candidate_coordinate_field

        field = field_iterator.next()

    return likely_coordinates_field if likely_coordinates_field is not None else candidate_coordinate_field


def _is_user_field(field):
    """
    Determine if a field is a user field or internal field, return True if the
    given field is a user field and False if it isn't.
    """
    INTERNAL_FIELD_NAMES = ['cmiss_number', 'xi', 'coordinates']
    return field.getName() not in INTERNAL_FIELD_NAMES


def _find_available_fields(field_module):
    """
    Excludes the expected 'coordinates' field by default.
    """
    field_iterator = field_module.createFielditerator()
    field = field_iterator.next()
    available_fields = []
    group_fields = []
    while field.isValid():
        group_field = field.castGroup()
        if _is_user_field(field) and not group_field.isValid():
            available_fields.append(field)
        elif group_field.isValid():
            group_fields.append(group_field)

        field = field_iterator.next()

    return available_fields, group_fields


def extract_mesh_info(region):
    mesh_info = None
    field_module = region.getFieldmodule()
    mesh_1d = field_module.findMeshByDimension(1)
    analysis_elements = [None] * mesh_1d.getSize()
    element_iterator = mesh_1d.createElementiterator()
    element = element_iterator.next()
    index = 0
    coordinates_field = _find_likely_coordinate_field(field_module)
    coordinates_field.setName("coordinates")
    available_fields, group_fields = _find_available_fields(field_module)
    available_fields.insert(0, coordinates_field)

    # _print_check_on_field_names(available_fields)

    # Assumes all elements define the same element field template.
    eft = element.getElementfieldtemplate(coordinates_field, -1)
    local_nodes_count = eft.getNumberOfLocalNodes()
    if local_nodes_count == 2:
        element_identifier_to_index_map = {}
        node_fields = {available_field.getName(): available_field for available_field in available_fields}
        nodes = []
        node_identifier_to_index_map = {}
        while element.isValid():
            element_identifier = element.getIdentifier()
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

        forest = determine_forest(analysis_elements)

        mesh_info = classify_forest(forest, nodes, node_identifier_to_index_map, node_fields, group_fields)

    return mesh_info


def _print_check_on_field_names(available_fields):  # pragma: no cover
    print('Check field name for internal fields.')
    CHECKED_FIELD_NAMES = ['coordinates', 'radius', 'rgb']
    for a in available_fields:
        if a.getName() not in CHECKED_FIELD_NAMES:
            print(a.getName())
    print('Check complete.')

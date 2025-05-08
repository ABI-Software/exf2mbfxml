import os

from cmlibs.utils.zinc.field import field_is_managed_coordinates
from cmlibs.zinc.context import Context
from cmlibs.zinc.result import RESULT_OK

from exf2mbfxml.analysis import determine_forest, classify_forest
from exf2mbfxml.classes import Node, Element
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


def extract_mesh_info(region):
    mesh_info = None
    field_module = region.getFieldmodule()
    # field_cache = field_module.createFieldcache()
    mesh_1d = field_module.findMeshByDimension(1)
    analysis_elements = [None] * mesh_1d.getSize()
    element_iterator = mesh_1d.createElementiterator()
    element = element_iterator.next()
    index = 0
    coordinates_field = _find_likely_coordinate_field(field_module)
    coordinates_field.setName("coordinates")
    radius_field = field_module.findFieldByName("radius")
    rgb_field = field_module.findFieldByName("rgb")
    # Assumes all elements define the same element field template.
    eft = element.getElementfieldtemplate(coordinates_field, -1)
    local_nodes_count = eft.getNumberOfLocalNodes()
    if local_nodes_count == 2:
        element_identifier_to_index_map = {}
        node_fields = {}
        for field in [coordinates_field, radius_field, rgb_field]:
            if field.isValid():
                node_fields[field.getName()] = field
        nodes = []
        node_identifier_to_index_map = {}
        while element.isValid():
            local_node_identifiers = []
            for i in range(local_nodes_count):
                node = element.getNode(eft, i + 1)
                node_identifier = node.getIdentifier()
                if node_identifier not in node_identifier_to_index_map:
                    node_identifier_to_index_map[node_identifier] = len(nodes)
                    nodes.append(node)
                # field_cache.setNode(node)
                # location_result, location = coordinate_field.evaluateReal(field_cache, 3)
                local_node_identifiers.append(node_identifier)
            element_identifier = element.getIdentifier()
            # Element(element_identifier, local_node_identifiers[0], local_node_identifiers[1])
            analysis_elements[index] = {"id": element_identifier, "nodes": local_node_identifiers}
            element_identifier_to_index_map[element_identifier] = index
            element = element_iterator.next()
            index += 1

        forest = determine_forest(analysis_elements)

        mesh_info = classify_forest(forest, analysis_elements, element_identifier_to_index_map, nodes, node_identifier_to_index_map, node_fields)

    return mesh_info

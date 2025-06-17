from cmlibs.zinc.field import Field
from cmlibs.zinc.result import RESULT_OK, RESULT_ERROR_GENERAL

from exf2mbfxml.utilities import rgb_to_hex


def get_point(node, fields):
    coordinate_field = fields["coordinates"]
    field_module = coordinate_field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    values = [-1, -1, -1, 1]
    result, coordinates = coordinate_field.evaluateReal(field_cache, 3)

    if result == RESULT_OK:
        radius_field = fields.get("radius")
        diameter = 1.0
        if radius_field is not None:
            result, value = radius_field.evaluateReal(field_cache, 1)
            if result == RESULT_OK:
                diameter = 2 * value

        values = [*coordinates, diameter]

    return values


def get_string(node, field_name):
    nodeset = node.getNodeset()
    field_module = nodeset.getFieldmodule()
    name_field = field_module.findFieldByName(field_name)
    return _evaluate_field(node, name_field, Field.VALUE_TYPE_STRING, "")


def get_markers(region):
    markers = []
    field_module = region.getFieldmodule()
    marker_group = field_module.findFieldByName("marker").castGroup()
    if marker_group.isValid():
        datapoints = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        marker_nodeset_group = marker_group.getNodesetGroup(datapoints)
        datapoint_iter = marker_nodeset_group.createNodeiterator()
        datapoint = datapoint_iter.next()
        while datapoint.isValid():
            markers.append(datapoint)
            datapoint = datapoint_iter.next()

    return markers


def _evaluate_field(node, field, value_type, default_value=None):
    value = default_value
    if field is not None:
        field_module = field.getFieldmodule()
        field_cache = field_module.createFieldcache()
        field_cache.setNode(node)
        if value_type == Field.VALUE_TYPE_STRING:
            potential_value = field.evaluateString(field_cache)
            result = RESULT_ERROR_GENERAL if value is None else RESULT_OK
        elif value_type == Field.VALUE_TYPE_MESH_LOCATION:
            raise NotImplementedError('Evaluate mesh location field not implemented.')
        elif value_type == Field.VALUE_TYPE_REAL:
            result, potential_value = field.evaluateReal(field_cache, field.getNumberOfComponents())
        else:
            raise ValueError(f'No available evaluation for this type :{value_type}')

        value = potential_value if result == RESULT_OK else value

    return value


def get_colour(node, fields):
    result = _evaluate_field(node, fields.get('rgb'), Field.VALUE_TYPE_REAL, default_value=[0, 0, 0])
    return rgb_to_hex(result)


def get_resolution(node, fields):
    return _evaluate_field(node, fields.get('resolution'), Field.VALUE_TYPE_REAL)


def get_group_elements_and_nodes(group_fields):
    grouped_elements = {}
    field_module = None
    mesh = None
    node_set = None

    for group_field in group_fields:
        if field_module is None:
            field_module = group_field.getFieldmodule()
            node_set = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            mesh = field_module.findMeshByDimension(1)

        node_set_group = group_field.getNodesetGroup(node_set)
        node_iterator = node_set_group.createNodeiterator()
        node_ids = set()
        node = node_iterator.next()
        while node.isValid():
            node_ids.add(node.getIdentifier())
            node = node_iterator.next()

        mesh_group = group_field.getMeshGroup(mesh)
        element_iterator = mesh_group.createElementiterator()
        element_ids = set()
        element = element_iterator.next()
        while element.isValid():
            element_ids.add(element.getIdentifier())
            element = element_iterator.next()

        grouped_elements[group_field.getName()] = {'nodes': node_ids, 'elements': element_ids}

    return grouped_elements


def get_group_nodes(group_fields):
    grouped_nodes = {}
    field_module = None
    node_set = None

    for group_field in group_fields:
        if field_module is None:
            field_module = group_field.getFieldmodule()
            node_set = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

        node_set_group = group_field.getNodesetGroup(node_set)
        node_iterator = node_set_group.createNodeiterator()
        node_ids = set()
        node = node_iterator.next()
        while node.isValid():
            node_ids.add(node.getIdentifier())
            node = node_iterator.next()
        grouped_nodes[group_field.getName()] = node_ids

    return grouped_nodes

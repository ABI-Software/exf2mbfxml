from cmlibs.zinc.result import RESULT_OK

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


def get_colour(node, fields):
    rgb_field = fields.get("rgb")
    colour = "#000000"
    if rgb_field is not None:
        field_module = rgb_field.getFieldmodule()
        field_cache = field_module.createFieldcache()
        field_cache.setNode(node)
        result, value = rgb_field.evaluateReal(field_cache, rgb_field.getNumberOfComponents())
        if result == RESULT_OK:
            colour = rgb_to_hex(value)

    return colour


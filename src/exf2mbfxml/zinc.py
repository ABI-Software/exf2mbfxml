from cmlibs.zinc.result import RESULT_OK


def get_point(node, fields):
    coordinate_field = fields["coordinates"]
    field_module = coordinate_field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    result, values = coordinate_field.evaluateReal(field_cache, 3)

    if result == RESULT_OK:
        radius_field = fields.get("radius")
        diameter = 1.0
        if radius_field is not None:
            result, value = radius_field.evaluateReal(field_cache, 1)
            if result == RESULT_OK:
                diameter = 2 * value

        values.append(diameter)
        return values

    return []

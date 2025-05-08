from cmlibs.zinc.result import RESULT_OK


class Node:
    def __init__(self, zinc_node, coordinate_field):
        self.id = zinc_node.getIdentifier()
        self._node = zinc_node
        self._coordinate_field = coordinate_field

    def get_point(self):
        field_module = self._coordinate_field.getFieldmodule()
        field_cache = field_module.createFieldcache()
        field_cache.setNode(self._node)
        result, values = self._coordinate_field.evaluateReal(field_cache, 3)
        if result == RESULT_OK:
            return values


class Element:
    def __init__(self, identifier, node1, node2):
        self.id = identifier
        self.nodes = (node1, node2)

    def start_point(self):
        return self.nodes[0].get_point()

    def end_point(self):
        return self.nodes[1].get_point()

import os
import unittest

import xml.etree.ElementTree as ET

from unittest.mock import patch

from exf2mbfxml.analysis import is_suitable_mesh
from exf2mbfxml.app import main
from exf2mbfxml.exceptions import EXFFile
from exf2mbfxml.reader import read_exf
from exf2mbfxml.writer import write_mbfxml

here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


missing_exf_file = _resource_path("missing.exf")
empty_exf_file = _resource_path("xml_file.exf")
basic_contour_exf_file = _resource_path("basic_contour.exf")
test_output_mbf = _resource_path("command_line_mbf.xml")


class MainTestCase(unittest.TestCase):

    @patch('sys.argv', ['app.py', missing_exf_file])
    def test_not_existing_exf_file(self):
        self.assertEqual(1, main())

    @patch('sys.argv', ['app.py', empty_exf_file])
    def test_failed_read_file(self):
        self.assertEqual(2, main())

    @patch('sys.argv', ['app.py', basic_contour_exf_file, '--output-mbf', test_output_mbf])
    def test_output_location(self):
        self.assertEqual(0, main())


class EXFReadModelTestCase(unittest.TestCase):

    def test_not_existing_xml_file(self):
        self.assertRaises(EXFFile, read_exf, missing_exf_file)

    def test_basic_contour(self):
        content = read_exf(basic_contour_exf_file)
        self.assertIsNotNone(content)
        write_mbfxml(f"{basic_contour_exf_file}.xml", content, {})

    def test_heart_contour(self):
        basic_heart_contour_exf_file = _resource_path("basic_heart_contours.exf")
        content = read_exf(basic_heart_contour_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{basic_heart_contour_exf_file}.xml"
        write_mbfxml(output_xml_file, content, {})
        with open(output_xml_file) as fh:
            content = fh.readlines()
            line_count = 23
            self.assertEqual(line_count, len(content))


class EXFTreeTestCase(unittest.TestCase):

    def test_bad_input(self):
        output_xml_file = _resource_path("rm.xml")
        content = {'trees': [{}], 'contours': [{}]}
        write_mbfxml(output_xml_file, content)
        with open(output_xml_file) as fh:
            content = fh.readlines()
            line_count = 2
            self.assertEqual(line_count, len(content))

        os.remove(output_xml_file)

    def test_basic_tree(self):
        basic_tree_exf_file = _resource_path("basic_tree.exf")
        content = read_exf(basic_tree_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{basic_tree_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))

    def test_multi_tree_with_annotations(self):
        multi_tree_exf_file = _resource_path("multi_tree_with_annotations.exf")
        content = read_exf(multi_tree_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{multi_tree_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))

        expected_structure = [
            {'tag': 'contour', 'points': {'x': '668.78', 'y': '-415.46', 'z': '-75.50', 'd': '4.09'}},
            {'tag': 'contour', 'points': {'x': '645.60', 'y': '-1056.82', 'z': '-88.50', 'd': '4.09'}},
            {'tag': 'contour', 'points': {'x': '1200.86', 'y': '-972.36', 'z': '-153.50', 'd': '4.09'}},
            {'tag': 'contour', 'points': {'x': '-7.27', 'y': '-1288.34', 'z': '0.00', 'd': '17.44'}},
            {'tag': 'contour', 'points': {'x': '1299.23', 'y': '-1287.61', 'z': '-294.00', 'd': '15.99'}},
            {'tag': 'tree', 'points': {'x': '1101.16', 'y': '-973.74', 'z': '-80.50', 'd': '4.09'},
             'children':
                 [{'tag': 'branch', 'points': {'x': '1068.70', 'y': '-979.08', 'z': '-86.12', 'd': '4.09'}}]},
        ]
        self._compare_structure(output_xml_file, expected_structure)

    def _compare_structure(self, xml_file, structure):
        with open(xml_file) as fh:
            content = fh.read()
        computed_root = ET.fromstring(content)
        strip_namespace(computed_root)

        self._compare_children(computed_root, structure)

    def _compare_children(self, computed_root, structure):
        indexing = {}
        for index, expected_child in enumerate(structure):
            expected_child = structure[index]
            expected_tag = expected_child['tag']
            if expected_tag in indexing:
                indexing[expected_tag] += 1
            else:
                indexing[expected_tag] = 0
            children = computed_root.findall(expected_tag)
            computed_child = children[indexing[expected_tag]]
            self.assertEqual(expected_child.get('tag'), computed_child.tag)
            computed_first_point = computed_child.find('point')
            expected_point = expected_child.get('points')
            exp_pt_values = [expected_point.get(p) for p in expected_point]
            com_pt_values = [computed_first_point.attrib.get(k) for k in computed_first_point.attrib]
            self.assertListEqual(exp_pt_values, com_pt_values)
            if expected_child.get('children', []):
                self._compare_children(computed_child, expected_child['children'])

    def test_multi_tree_with_branches(self):
        branched_tree_exf_file = _resource_path("tree_with_branches.exf")
        content = read_exf(branched_tree_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{branched_tree_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))
        with open(output_xml_file) as fh:
            content = fh.readlines()
            line_count = 79
            self.assertEqual(line_count, len(content))


class EXFVesselTestCase(unittest.TestCase):

    def test_bad_input(self):
        output_xml_file = _resource_path("rm.xml")
        content = {'trees': [{}], 'contours': [{}], 'vessels': [{}]}
        write_mbfxml(output_xml_file, content)
        with open(output_xml_file) as fh:
            content = fh.readlines()
            line_count = 2
            self.assertEqual(line_count, len(content))

        os.remove(output_xml_file)

    def test_is_suitable(self):
        basic_tree_exf_file = _resource_path("simple_vessel_structure.exf")
        self.assertTrue(is_suitable_mesh(basic_tree_exf_file))

    def test_simple_vessel(self):
        basic_tree_exf_file = _resource_path("simple_vessel_structure.exf")
        content = read_exf(basic_tree_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{basic_tree_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))
        with open(output_xml_file) as fh:
            content = fh.readlines()
            line_count = 98
            self.assertEqual(line_count, len(content))


class EXFMarkerTestCase(unittest.TestCase):

    def test_bad_input(self):
        vessel_exf_file = _resource_path("simple_vessel_structure.exf")
        content = read_exf(vessel_exf_file)
        marker_count = 0
        self.assertEqual(marker_count, len(content['markers']))

    def test_markers(self):
        marker_exf_file = _resource_path("contour_with_marker_names.exf")
        content = read_exf(marker_exf_file)
        marker_count = 11
        self.assertEqual(marker_count, len(content['markers']))
        output_xml_file = f"{marker_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))


class RealWorldTestCase(unittest.TestCase):

    def test_japanese_vagus_valid(self):
        basic_tree_exf_file = _resource_path("japanese_vagus.exf")
        self.assertTrue(is_suitable_mesh(basic_tree_exf_file))

    def test_japanese_vagus(self):
        japanese_exf_file = _resource_path("japanese_vagus.exf")
        content = read_exf(japanese_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{japanese_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))


def strip_namespace(tree):
    for elem in tree.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]  # Remove namespace
    return tree


if __name__ == "__main__":
    unittest.main()

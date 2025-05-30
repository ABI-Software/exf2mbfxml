import os
import unittest

from unittest.mock import patch

from exf2mbfxml.app import main
from exf2mbfxml.exceptions import EXFFile
from exf2mbfxml.reader import read_exf
from exf2mbfxml.utilities import get_identifiers_from_path
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


class EXFTreeTestCase(unittest.TestCase):

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

    def test_multi_tree_with_branches(self):
        branched_tree_exf_file = _resource_path("tree_with_branches.exf")
        content = read_exf(branched_tree_exf_file)
        self.assertIsNotNone(content)
        output_xml_file = f"{branched_tree_exf_file}.xml"
        write_mbfxml(output_xml_file, content)
        self.assertTrue(os.path.isfile(output_xml_file))


if __name__ == "__main__":
    unittest.main()

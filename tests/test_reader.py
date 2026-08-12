import unittest

from cmlibs.zinc.context import Context
from cmlibs.zinc.result import RESULT_OK

from exf2mbfxml.reader import extract_mesh_info

try:
    from utils import resource_path
except ImportError:
    from .utils import resource_path


class TestMeshInfo(unittest.TestCase):
    def test_extract_mesh_info(self):
        exf_file = resource_path("vagus_scaffold.exf")
        context = Context("read")
        region = context.createRegion()
        result = region.readFile(exf_file)

        self.assertTrue(result == RESULT_OK)

        mesh_info = extract_mesh_info(region)

        self.assertEqual(['contours', 'trees', 'vessels', 'markers'], list(mesh_info.keys()))
        self.assertEqual(1, len(mesh_info['trees']))
        self.assertEqual(0, len(mesh_info['markers']))
        self.assertEqual(0, len(mesh_info['vessels']))
        self.assertEqual(0, len(mesh_info['contours']))

if __name__ == "__main__":
    unittest.main()


import unittest

from exf2mbfxml.utilities import nest_multiple_sequences, find_matching_subsequence


class TestNestingFunctions(unittest.TestCase):
    def test_already_nested(self):
        data = [1, 2, [3, 4, [5, [6, 7]]]]
        sequences = [[3, 4], [5]]
        expected = [1, 2, [3, 4, [5, [6, 7]]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_single_value_already_nested(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, [14, 15, 16, 17, 18]]]
        sequences = [{9}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, [14, 15, 16, 17, 18]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_simple_middle_input_needing_nesting(self):
        data = [1, 2, 3, 4, 5, 6, 7]
        sequences = [[4, 5]]
        expected = [1, 2, 3, [4, 5, [6, 7]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_simple_end_input_needing_nesting(self):
        data = [1, 2, 3, 4, 5, 6, 7]
        sequences = [[6, 7]]
        expected = [1, 2, 3, 4, 5, [6, 7]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_flat_input_needing_nesting(self):
        data = [1, 2, 3, 4, 5, [6, 7]]
        sequences = [[3, 4], [5]]
        expected = [1, 2, [3, 4, [5, [6, 7]]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_deep_input_needing_nesting(self):
        data = [1, 2, [3, 4, 5, [6, 7]]]
        sequences = [[4, 5]]
        expected = [1, 2, [3, [4, 5, [6, 7]]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_multi_level_input_I(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, 15, 16, 17, 18]]
        sequences = [{13}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, [14, 15, 16, 17, 18]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_multi_level_input_II(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, 15, 16, 17, 18]]
        sequences = [{13, 14}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, [15, 16, 17, 18]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_multi_level_input_III(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, 15, 16, 17, 18]]
        sequences = [{15, 16}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, [15, 16, [17, 18]]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_multi_level_input_IV(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, 15, 16, 17, 18]]
        sequences = [{15, 16, 17}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [10], [11, 12]], [13, 14, [15, 16, 17, [18]]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_large_sequence(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, [9, [[10], [11, 12]]], [13, [14, 15, 16, 17, 18]]]
        sequences = [{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}]
        expected = [1, 2, 3, 4, 5, 6, 7, 8, [9, [[10], [11, 12]]], [13, [14, 15, 16, 17, 18]]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_missing_sequence(self):
        data = [1, 2, 3, 4, 5, [6, 7]]
        sequences = [[8, 9]]
        expected = [1, 2, 3, 4, 5, [6, 7]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_empty_input(self):
        data = []
        sequences = [[3, 4], [5]]
        expected = []
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_empty_sequence_list(self):
        data = [1, 2, 3, 4, 5, [6, 7]]
        sequences = []
        expected = [1, 2, 3, 4, 5, [6, 7]]
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))

    def test_invalid_input_list(self):
        data = None
        sequences = [{4, 5, 6}]
        expected = []
        self.assertEqual(expected, nest_multiple_sequences(data, sequences))


class TestFindSubsequenceFunctions(unittest.TestCase):
    def test_exists(self):
        data = [1, 2, 3, 4, [5, [6, 7]]]
        sequence = {3, 4}
        self.assertEqual(2, find_matching_subsequence(data, sequence))

    def test_doesnt_exist(self):
        data = [1, 2, 3, 4, [5, [6, 7]]]
        sequence = {3, 5}
        self.assertIsNone(find_matching_subsequence(data, sequence))

    def test_empty_input_list(self):
        data = []
        sequence = {1, 2}
        self.assertIsNone(find_matching_subsequence(data, sequence))

    def test_empty_sequence(self):
        data = [1, 2, 3, 4, [5, [6, 7]]]
        sequence = {}
        self.assertIsNone(find_matching_subsequence(data, sequence))


if __name__ == '__main__':
    unittest.main()

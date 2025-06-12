import xml.etree.ElementTree as ET

from cmlibs.utils.zinc.field import field_is_managed_coordinates


def rgb_to_hex(rgb_value):
    """
    Convert a list of values between [0, 1] into a string representation using a leading #.

      E.g. [0, 1, 0] --> #00ff00

    :return: The value of the three element list with values in the range [0. 1] as a hexadecimal string.
    """

    # Scale the values from 0-1 to 0-255 and convert to integers
    scaled_values = [int(255 * value) for value in rgb_value]
    # Format the values as a hex string
    return '#{:02x}{:02x}{:02x}'.format(*scaled_values).upper()


def is_sequence_nested(data, sequence):
    if not isinstance(data, list):
        return False
    if data[:len(sequence)] == sequence:
        return True

    return any(is_sequence_nested(item, sequence) for item in data if isinstance(item, list))


def nest_sequence(data, sequence):
    if not isinstance(data, list):
        return []

    sequence_length = len(sequence)
    data_length = len(data)
    if isinstance(sequence, list):
        sequence = set(sequence)

    matchable_data = collect_integers_until_non_integer(data)
    if set(matchable_data) == sequence:
        return data

    result = []
    i = 0
    while i < data_length:
        i_end = i + sequence_length
        window = data[i:i_end]

        if isinstance(data[i], list):
            result.append(nest_sequence(data[i], sequence))
        elif is_matching_subsequence(window, sequence):
            rest = data[i_end:]
            if i == 0:
                result.extend(window)
                result.append(rest)
            elif not rest:
                result.append(window)
            elif len(rest) == 1 and isinstance(rest[0], list):
                result.append([*window, *rest])
            else:
                result.append([*window, rest])
            break
        else:
            result.append(data[i])

        i += 1

    return result


def nest_multiple_sequences(data, sequences):
    for seq in sequences:
        if not is_sequence_nested(data, seq):
            data = nest_sequence(data, seq)
    return data


def is_matching_subsequence(input_list, sequence_set):
    try:
        subsequence_set = set(input_list)
    except TypeError:
        return False

    if subsequence_set == sequence_set:
        return True

    return False


def find_matching_subsequence(input_list, sequence_set):
    sequence_length = len(sequence_set)

    for i in range(len(input_list) - sequence_length + 1):
        if is_matching_subsequence(input_list[i:i + sequence_length], sequence_set):
            return i

    return None


def collect_integers_until_non_integer(input_list):
    result = []
    for item in input_list:
        if isinstance(item, int):
            result.append(item)
        else:
            break
    return result


def get_unique_list_paths(nested_list):
    if not isinstance(nested_list, list):
        return None

    trace = {}

    def _helper(nested_list_local, path=None):
        if path is None:
            path = []
        i = 0
        while i < len(nested_list_local):
            current_path = path + [i]
            if isinstance(nested_list_local[i], list):
                _helper(nested_list_local[i], current_path)
            elif i == 0:
                trace[tuple(current_path)] = 1
            i += 1

    _helper(nested_list)
    return list(trace.keys())


def get_identifiers_from_path(path, nested_list):
    if not isinstance(path, tuple) or not isinstance(nested_list, list):
        return None

    try:
        target_list = nested_list
        for index in path[:-1]:
            target_list = target_list[index]

        return [item for item in target_list if isinstance(item, int)]
    except (IndexError, TypeError):
        return None


def is_valid_xml(xml_string):
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError:
        return False


def find_likely_coordinate_field(field_module):
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


def find_available_fields(field_module):
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


def determine_fields(field_module):
    coordinates_field = find_likely_coordinate_field(field_module)
    coordinates_field.setName("coordinates")
    available_fields, group_fields = find_available_fields(field_module)
    available_fields.insert(0, coordinates_field)
    return coordinates_field, available_fields, group_fields

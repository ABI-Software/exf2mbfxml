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

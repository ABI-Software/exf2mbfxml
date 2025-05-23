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

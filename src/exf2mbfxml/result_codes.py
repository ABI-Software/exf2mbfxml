
return_codes = ['SUCCESS', 'MISSING_INPUT_FILE', 'FAILED_TO_READ_EXF']

globals().update({code: index for index, code in enumerate(return_codes)})

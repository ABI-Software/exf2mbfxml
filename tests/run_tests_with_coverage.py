import coverage
import os

here = os.path.abspath(os.path.dirname(__file__))


def run_tests():

    cov = coverage.Coverage(source=['exf2mbfxml'])
    cov.start()

    import unittest

    loader = unittest.TestLoader()
    suite = loader.discover(here)
    runner = unittest.TextTestRunner()
    runner.run(suite)

    cov.stop()
    cov.save()
    cov.report(skip_covered=True, skip_empty=True, show_missing=True)

    # Delete the .coverage file
    if os.path.exists('.coverage'):
        os.remove('.coverage')
        print(".coverage file deleted")


if __name__ == '__main__':
    run_tests()

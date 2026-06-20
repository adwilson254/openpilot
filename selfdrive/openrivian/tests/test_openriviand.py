import unittest

class TestOpenRivianAPI(unittest.TestCase):
    def test_import_openriviand(self):
        """
        Verify that the openriviand API daemon can be imported without syntax
        or runtime initialization errors.
        """
        try:
            from selfdrive.openrivian.api import openriviand
            self.assertIsNotNone(openriviand)
        except Exception as e:
            self.fail(f"Failed to import openriviand: {e}")

if __name__ == "__main__":
    unittest.main()

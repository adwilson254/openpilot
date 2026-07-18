import unittest

class TestWebDashboard(unittest.TestCase):
    def test_import_webd(self):
        """
        Verify that the web dashboard daemon can be imported without syntax
        errors and that its dependencies are resolvable.
        """
        try:
            from selfdrive.openrivian import webd
            self.assertIsNotNone(webd)
        except Exception as e:
            self.fail(f"Failed to import webd: {e}")

if __name__ == "__main__":
    unittest.main()

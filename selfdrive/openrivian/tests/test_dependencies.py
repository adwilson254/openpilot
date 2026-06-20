import unittest
import importlib

class TestOpenRivianDependencies(unittest.TestCase):
    def test_production_dependencies(self):
        """
        Verify that all core Python packages required for OpenRivian daemons 
        to execute on the Comma device are correctly installed and resolvable in the environment.
        """
        required_packages = [
            "flask",
            "flask_cors",
            "paho.mqtt",
            "fastapi",
            "uvicorn",
            "cereal",
            "openpilot.common"
        ]

        missing_packages = []
        for pkg in required_packages:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing_packages.append(pkg)

        self.assertEqual(len(missing_packages), 0, f"Missing production dependencies: {missing_packages}. "
                                                   f"These must be available on the Comma device environment.")

if __name__ == "__main__":
    unittest.main()

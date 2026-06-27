import unittest
import importlib


class TestOpenRivianDependencies(unittest.TestCase):
    def test_production_dependencies(self):
        """Verify the packages the OpenRivian daemons actually import are resolvable
        in the device/CI environment.

        This list is derived from the real import surface, not historical guesses:
          - paho.mqtt      -> cereal2mqtt, mqtt2params (MQTT client)
          - amqtt          -> mqttd (in-RAM broker; requires Python >= 3.10)
          - requests       -> api/rivian_api (Rivian GraphQL calls)
          - cereal         -> cereal2mqtt (SubMaster / messaging)
          - openpilot.common -> mqtt2params, api/* (Params, swaglog)

        webd uses only the stdlib (http.server/socketserver) and is intentionally
        absent. flask/flask_cors/fastapi/uvicorn were removed (F3) and are NOT
        imported anywhere; asserting them here previously locked in dead deps and
        risked a false CI failure.
        """
        required_packages = [
            "paho.mqtt",
            "amqtt",
            "requests",
            "cereal",
            "openpilot.common",
        ]

        missing_packages = []
        for pkg in required_packages:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing_packages.append(pkg)

        self.assertEqual(
            len(missing_packages), 0,
            f"Missing production dependencies: {missing_packages}. "
            f"These must be available on the Comma device environment.",
        )


if __name__ == "__main__":
    unittest.main()

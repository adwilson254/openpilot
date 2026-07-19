import unittest

class TestMQTTDaemons(unittest.TestCase):
    def test_import_mqtt(self):
        """
        Verify that the MQTT daemons can be imported without syntax errors.
        """
        try:
            from selfdrive.openrivian import mqttd
            from selfdrive.openrivian import cereal2mqtt
            from selfdrive.openrivian import mqtt2params
            self.assertIsNotNone(mqttd)
            self.assertIsNotNone(cereal2mqtt)
            self.assertIsNotNone(mqtt2params)
        except Exception as e:
            self.fail(f"Failed to import MQTT daemons: {e}")

if __name__ == "__main__":
    unittest.main()

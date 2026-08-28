import unittest
from api.routes import get_system_ram_metrics, get_gpu_metrics, get_tunnel_metrics


class ObservabilityAndMonitoringTests(unittest.TestCase):
    def test_ram_metrics_structure(self):
        ram = get_system_ram_metrics()
        self.assertTrue("totalBytes" in ram or "status" in ram or "error" in ram)
        if "totalBytes" in ram:
            self.assertGreater(ram["totalBytes"], 0)
            self.assertIn("usedPercent", ram)

    def test_gpu_metrics_structure(self):
        gpu = get_gpu_metrics()
        self.assertIn("type", gpu)
        self.assertIn("available", gpu)

    def test_tunnel_metrics_structure(self):
        tunnel = get_tunnel_metrics()
        self.assertIn("status", tunnel)
        self.assertIn("processRunning", tunnel)


if __name__ == "__main__":
    unittest.main()

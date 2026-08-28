import tempfile
import time
import unittest
from pathlib import Path

from config import PROXIES_DIR, CONFORMED_DIR
from engine.proxy_manager import ProxyManager


class ProxyAndCacheTests(unittest.TestCase):
    def test_cache_stats(self):
        stats = ProxyManager.cache_stats()
        self.assertIn("proxies", stats)
        self.assertIn("conformed", stats)
        self.assertIn("totalCacheMB", stats)

    def test_cache_prune_ttl_and_lru(self):
        with tempfile.TemporaryDirectory() as folder:
            # Create dummy proxy files in PROXIES_DIR
            test_file = PROXIES_DIR / "proxy_test_lru.mp4"
            test_file.write_bytes(b"0" * 1000)

            # Pruning with small limit removes files
            res = ProxyManager.prune_cache(max_size_bytes=100, max_age_seconds=0)
            self.assertGreaterEqual(res["deletedFiles"], 1)
            self.assertFalse(test_file.exists())

    def test_probe_media_non_existent(self):
        res = ProxyManager.probe_media(Path("/non/existent/video.mp4"))
        self.assertFalse(res.get("available", True))


if __name__ == "__main__":
    unittest.main()

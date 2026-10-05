"""Vigila que la defensa contra SSRF del backend (dominio.py) y la del worker (logica.py) no se desincronicen."""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dominio  # noqa: E402

RUTA_WORKER = Path(__file__).resolve().parents[2] / "worker" / "logica.py"

IPS = ["8.8.8.8", "1.1.1.1", "2606:4700::1111", "127.0.0.1", "10.0.0.1", "172.16.5.4", "192.168.0.1", "169.254.169.254", "100.64.0.1",
       "0.0.0.0", "::", "::1", "::ffff:10.0.0.1", "::ffff:8.8.8.8", "224.0.0.1", "fe80::1", "fd00::1", "255.255.255.255", "192.0.2.1", "198.51.100.7"]


@unittest.skipUnless(RUTA_WORKER.exists(), "worker/logica.py no está en este árbol")
class Paridad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("logica_worker", RUTA_WORKER)
        cls.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.worker)

    def test_ip_prohibida_coincide(self):
        for ip in IPS:
            for permitir in (False, True):
                self.assertEqual(
                    dominio.ip_prohibida(ip, permitir), self.worker.ip_prohibida(ip, permitir),
                    f"backend y worker discrepan con {ip} (permitir_privados={permitir}): actualiza los dos",
                )

    def test_urls_con_ip_literal_coinciden(self):
        for ip in IPS:
            host = f"[{ip}]" if ":" in ip else ip
            url = f"http://{host}/"
            for permitir in (False, True):
                try:
                    dominio.validar_url(url, permitir)
                    backend_acepta = True
                except ValueError:
                    backend_acepta = False
                self.assertEqual(backend_acepta, self.worker.objetivo_permitido(url, permitir, lambda h, p: []), f"{url} permitir={permitir}")


if __name__ == "__main__":
    unittest.main()

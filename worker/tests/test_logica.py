"""Pruebas de la lógica pura del worker. Se ejecutan con:  python -m unittest discover -s tests -v   (desde worker/)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logica  # noqa: E402


class Clasificar(unittest.TestCase):
    def test_tabla(self):
        casos = [
            (200, 100, 1200, "up"), (204, 1200, 1200, "up"), (301, 50, 1200, "up"),
            (200, 1201, 1200, "degraded"), (200, 5000, 1200, "degraded"),
            (400, 10, 1200, "degraded"), (404, 10, 1200, "degraded"), (429, 10, 1200, "degraded"),
            (500, 10, 1200, "down"), (502, 10, 1200, "down"), (503, 9999, 1200, "down"), (599, 1, 1200, "down"),
        ]
        for codigo, lat, umbral, esperado in casos:
            self.assertEqual(logica.clasificar(codigo, lat, umbral), esperado, (codigo, lat))

    def test_el_umbral_es_configurable(self):
        self.assertEqual(logica.clasificar(200, 1500, 1200), "degraded")
        self.assertEqual(logica.clasificar(200, 1500, 2500), "up")  # DeepSeek responde ~1.1-2.6 s: con otro umbral deja de oscilar


class ObjetivoPermitido(unittest.TestCase):
    def resolver(self, tabla):
        def f(host, puerto):
            if host not in tabla:
                raise OSError("no resuelve")
            return tabla[host]
        return f

    def test_nombre_publico_pasa(self):
        self.assertTrue(logica.objetivo_permitido("https://api.openai.com/v1", False, self.resolver({"api.openai.com": ["104.18.1.1"]})))

    def test_nombre_publico_que_resuelve_a_ip_interna_se_bloquea(self):
        # el ataque clásico: un dominio "público" apuntando a la red interna
        for ip in ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"]:
            self.assertFalse(logica.objetivo_permitido("https://malo.example.com", False, self.resolver({"malo.example.com": [ip]})), ip)

    def test_basta_una_ip_interna_entre_varias(self):
        self.assertFalse(logica.objetivo_permitido("https://x.com", False, self.resolver({"x.com": ["8.8.8.8", "10.0.0.1"]})))

    def test_metadatos_de_la_nube_nunca_aun_permitiendo_privados(self):
        self.assertFalse(logica.objetivo_permitido("http://x.com", True, self.resolver({"x.com": ["169.254.169.254"]})))
        self.assertFalse(logica.objetivo_permitido("http://169.254.169.254/latest", True, self.resolver({})))

    def test_permitir_privados(self):
        self.assertTrue(logica.objetivo_permitido("http://localhost:8001", True, self.resolver({"localhost": ["127.0.0.1"]})))
        self.assertTrue(logica.objetivo_permitido("http://192.168.1.5", True, self.resolver({})))

    def test_ip_literal_sin_resolver(self):
        self.assertTrue(logica.objetivo_permitido("https://8.8.8.8/", False, self.resolver({})))
        self.assertFalse(logica.objetivo_permitido("http://127.0.0.1:8001", False, self.resolver({})))
        self.assertFalse(logica.objetivo_permitido("http://[::ffff:127.0.0.1]/", False, self.resolver({})))

    def test_si_no_resuelve_se_deja_pasar_para_que_quede_como_caida(self):
        self.assertTrue(logica.objetivo_permitido("https://no-existe.example.org", False, self.resolver({})))

    def test_urls_raras(self):
        for malo in ["file:///etc/passwd", "ftp://x.com", "https://", "http://:80", "javascript:alert(1)", "https://x.com:99999"]:
            self.assertFalse(logica.objetivo_permitido(malo, True, self.resolver({"x.com": ["8.8.8.8"]})), malo)


if __name__ == "__main__":
    unittest.main()

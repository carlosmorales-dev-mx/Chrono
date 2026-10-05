"""Pruebas de la lógica pura (backend/dominio.py). No necesitan base de datos ni red.

Se ejecutan con:   python -m unittest discover -s tests -v        (desde backend/)
y también con pytest.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dominio  # noqa: E402

UTC = timezone.utc


class ValidarNombre(unittest.TestCase):
    def test_normaliza_espacios(self):
        self.assertEqual(dominio.validar_nombre("  OpenAI API  "), "OpenAI API")

    def test_rechaza_vacio_y_largo_y_control(self):
        for malo in ["", "   ", None, "x" * 81, "uno\ndos", "tab\taqui", "nul\x00"]:
            with self.assertRaises(ValueError, msg=repr(malo)):
                dominio.validar_nombre(malo)

    def test_acepta_acentos_y_simbolos(self):
        self.assertEqual(dominio.validar_nombre("Cámara & Co. (prod)"), "Cámara & Co. (prod)")


class ValidarUrl(unittest.TestCase):
    def test_urls_publicas_validas(self):
        for ok in ["https://api.openai.com", "http://example.com/health", "https://status.deepseek.com/", "https://x.io:8443/a?b=1",
                   "https://8.8.8.8/", "https://[2606:4700:4700::1111]/", "  https://example.com  "]:
            self.assertEqual(dominio.validar_url(ok), ok.strip(), ok)

    def test_esquemas_peligrosos(self):
        for malo in ["file:///etc/passwd", "ftp://example.com", "javascript:alert(1)", "gopher://x", "data:text/html,hi", "//example.com", "example.com"]:
            with self.assertRaises(ValueError, msg=malo):
                dominio.validar_url(malo)

    def test_credenciales_en_la_url(self):
        for malo in ["https://user:pass@example.com", "https://user@example.com"]:
            with self.assertRaises(ValueError, msg=malo):
                dominio.validar_url(malo)

    def test_vacio_espacios_y_largo(self):
        for malo in ["", "   ", "https://exa mple.com", "https://example.com/" + "a" * 2100, "https://", "http://:80", "https://example.com:99999", "https://example.com:0"]:
            with self.assertRaises(ValueError, msg=malo[:50]):
                dominio.validar_url(malo)

    def test_ssrf_ips_internas_bloqueadas(self):
        internas = ["http://127.0.0.1", "http://127.0.0.1:8001", "http://10.0.0.5", "http://192.168.1.1", "http://172.16.0.1",
                    "http://100.64.0.1", "http://[::1]/", "http://0.0.0.0", "http://[::ffff:127.0.0.1]/", "http://[fd00::1]/"]
        for u in internas:
            with self.assertRaises(ValueError, msg=u):
                dominio.validar_url(u)

    def test_ssrf_metadatos_de_la_nube_siempre_bloqueados(self):
        for u in ["http://169.254.169.254/latest/meta-data/", "http://[fe80::1]/", "http://224.0.0.1/"]:
            for permitir in (False, True):  # ni siquiera con PERMITIR_OBJETIVOS_PRIVADOS
                with self.assertRaises(ValueError, msg=f"{u} permitir={permitir}"):
                    dominio.validar_url(u, permitir_privados=permitir)

    def test_nombres_internos_bloqueados(self):
        for u in ["http://localhost:8001", "http://LOCALHOST", "http://app.localhost", "http://impresora.local", "http://db.internal", "http://nas.lan", "http://localhost./"]:
            with self.assertRaises(ValueError, msg=u):
                dominio.validar_url(u)

    def test_permitir_privados_abre_lo_interno(self):
        for u in ["http://127.0.0.1:8001", "http://localhost:3000", "http://192.168.1.10", "http://10.1.2.3/health"]:
            self.assertEqual(dominio.validar_url(u, permitir_privados=True), u)

    def test_dominios_publicos_parecidos_a_internos_pasan(self):
        for u in ["https://localhost.example.com", "https://mylocal.com", "https://internal.example.org"]:
            self.assertEqual(dominio.validar_url(u), u)


class IpProhibida(unittest.TestCase):
    def test_tabla(self):
        casos = {"8.8.8.8": False, "1.1.1.1": False, "2606:4700::1111": False, "127.0.0.1": True, "10.0.0.1": True, "192.168.0.1": True,
                 "169.254.1.1": True, "100.100.0.1": True, "0.0.0.0": True, "::": True, "::1": True, "::ffff:10.0.0.1": True, "224.0.0.1": True}
        for ip, esperado in casos.items():
            self.assertEqual(dominio.ip_prohibida(ip), esperado, ip)

    def test_con_permitir_privados(self):
        self.assertFalse(dominio.ip_prohibida("127.0.0.1", permitir_privados=True))
        self.assertFalse(dominio.ip_prohibida("::ffff:10.0.0.1", permitir_privados=True))
        self.assertTrue(dominio.ip_prohibida("169.254.169.254", permitir_privados=True))


class DecidirIncidente(unittest.TestCase):
    def d(self, ultimos, abierto=None, a=2, c=3):
        return dominio.decidir_incidente(ultimos, abierto, a, c)

    def test_un_solo_chequeo_malo_no_abre(self):
        self.assertEqual(self.d(["degraded", "up", "up"]), dominio.NADA)
        self.assertEqual(self.d(["down"]), dominio.NADA)  # historia insuficiente

    def test_dos_malos_seguidos_abren(self):
        self.assertEqual(self.d(["degraded", "degraded", "up"]), ("abrir", "degraded"))

    def test_severidad_al_abrir_es_la_peor_de_la_ventana(self):
        self.assertEqual(self.d(["degraded", "down", "up"]), ("abrir", "down"))
        self.assertEqual(self.d(["down", "degraded"]), ("abrir", "down"))

    def test_abrir_tras_1_reproduce_el_comportamiento_anterior(self):
        self.assertEqual(self.d(["degraded"], a=1), ("abrir", "degraded"))
        self.assertEqual(self.d(["up", "down"], a=1), dominio.NADA)

    def test_un_chequeo_bueno_no_cierra(self):
        self.assertEqual(self.d(["up", "degraded", "degraded"], "degraded"), dominio.NADA)
        self.assertEqual(self.d(["up", "up", "degraded"], "degraded"), dominio.NADA)

    def test_tres_buenos_seguidos_cierran(self):
        self.assertEqual(self.d(["up", "up", "up", "degraded"], "degraded"), ("cerrar", None))

    def test_escala_cuando_empeora(self):
        self.assertEqual(self.d(["down", "degraded"], "degraded"), ("escalar", "down"))
        self.assertEqual(self.d(["down", "down"], "down"), dominio.NADA)  # ya está en lo peor
        self.assertEqual(self.d(["degraded", "down"], "down"), dominio.NADA)

    def test_sin_datos(self):
        self.assertEqual(self.d([]), dominio.NADA)

    def test_parametros_absurdos_se_corrigen(self):
        self.assertEqual(self.d(["down"], a=0), ("abrir", "down"))
        self.assertEqual(self.d(["up"], "down", c=0), ("cerrar", None))

    def simular(self, secuencia, a=2, c=3):
        """Ejecuta la decisión chequeo a chequeo, como lo hace el backend, y cuenta incidentes."""
        abiertos, cerrados, abierto, historial = 0, 0, None, []
        for e in secuencia:
            historial.insert(0, e)
            acc = dominio.decidir_incidente(historial, abierto, a, c)
            if acc.tipo == "abrir":
                abierto, abiertos = acc.severidad, abiertos + 1
            elif acc.tipo == "cerrar":
                abierto, cerrados = None, cerrados + 1
            elif acc.tipo == "escalar":
                abierto = acc.severidad
        return abiertos, cerrados, abierto

    def test_oscilacion_alrededor_del_umbral_no_genera_rachas(self):
        # DeepSeek: un chequeo lento, uno normal, uno lento… (justo el caso que llenaba de incidentes)
        oscila = ["up", "degraded"] * 30
        self.assertEqual(self.simular(oscila), (0, 0, None))
        # con el comportamiento anterior (abrir/cerrar a la primera) habría abierto 30 incidentes
        self.assertEqual(self.simular(oscila, a=1, c=1)[0], 30)

    def test_caida_real_abre_un_incidente_y_se_cierra_al_recuperarse(self):
        seq = ["up"] * 5 + ["down"] * 4 + ["up"] * 5
        self.assertEqual(self.simular(seq), (1, 1, None))

    def test_blip_de_recuperacion_dentro_de_un_incidente_no_lo_parte_en_dos(self):
        seq = ["up", "degraded", "degraded", "up", "degraded", "degraded", "up", "up", "up"]
        self.assertEqual(self.simular(seq), (1, 1, None))

    def test_escalada_y_cierre(self):
        seq = ["degraded", "degraded", "down", "down", "up", "up", "up"]
        self.assertEqual(self.simular(seq), (1, 1, None))


class AgruparHistorial(unittest.TestCase):
    AHORA = datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)

    def fila(self, minutos_atras, estado="up", lat=100):
        return (self.AHORA - timedelta(minutes=minutos_atras), estado, lat)

    def test_sin_datos(self):
        self.assertEqual(dominio.agrupar_historial([], self.AHORA), [])

    def test_servicio_recien_agregado_muestra_sus_puntos_reales(self):
        filas = [self.fila(m) for m in (5, 4, 3, 2, 1)]
        out = dominio.agrupar_historial(filas, self.AHORA)
        self.assertEqual(len(out), 5)  # nada de gráfica vacía hasta que pase una hora
        self.assertEqual([p["n"] for p in out], [1] * 5)

    def test_incluye_las_caidas_con_latencia_nula(self):
        filas = [self.fila(10, "up", 100), self.fila(9, "down", None), self.fila(8, "up", 120)]
        out = dominio.agrupar_historial(filas, self.AHORA)
        self.assertEqual([p["estado"] for p in out], ["up", "down", "up"])
        self.assertIsNone(out[1]["latencia_ms"])  # antes se descartaban y la caída era invisible

    def test_tramo_con_una_caida_corta_conserva_el_peor_estado(self):
        # 24 h de chequeos cada 30 s, con UN minuto caído en medio
        filas = []
        for i in range(2880):
            t = self.AHORA - timedelta(seconds=30 * (2880 - i))
            caido = 1440 <= i < 1442
            filas.append((t, "down" if caido else "up", None if caido else 100))
        out = dominio.agrupar_historial(filas, self.AHORA, horas=24, puntos_max=96)
        self.assertLessEqual(len(out), 97)
        self.assertGreaterEqual(len(out), 90)
        caidos = sum(1 for p in out if p["estado"] == "down")
        self.assertIn(caidos, (1, 2))  # 2 si la caída cae justo en el borde entre dos tramos; promediar la habría borrado
        self.assertEqual(sum(p["n"] for p in out), 2879)  # el chequeo del instante exacto -24 h queda fuera de la ventana

    def test_peor_estado_del_tramo_y_latencia_media(self):
        filas = [self.fila(3, "up", 100), self.fila(3, "degraded", 300), self.fila(3, "up", 200)]
        out = dominio.agrupar_historial(filas, self.AHORA)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["estado"], "degraded")
        self.assertEqual(out[0]["latencia_ms"], 200)
        self.assertEqual(out[0]["latencia_max"], 300)
        self.assertEqual(out[0]["n"], 3)

    def test_ordenado_y_fuera_de_ventana_excluido(self):
        filas = [self.fila(30 * 60, "up", 1), self.fila(5, "up", 5), self.fila(10, "up", 10)]  # la primera: hace 30 h
        out = dominio.agrupar_historial(filas, self.AHORA, horas=24)
        self.assertEqual([p["latencia_ms"] for p in out], [10, 5])

    def test_futuro_excluido(self):
        out = dominio.agrupar_historial([(self.AHORA + timedelta(minutes=5), "up", 1), self.fila(1)], self.AHORA)
        self.assertEqual(len(out), 1)

    def test_fechas_en_iso_con_zona(self):
        out = dominio.agrupar_historial([self.fila(1)], self.AHORA)
        self.assertTrue(out[0]["creado_en"].endswith("+00:00"))


class Percentil(unittest.TestCase):
    def test_coincide_con_percentile_cont(self):
        v = [100, 200, 300, 400, 500]
        self.assertEqual(dominio.percentil(v, 0.5), 300)
        self.assertEqual(dominio.percentil(v, 0.95), 480)   # 400 + 0.8 * 100
        self.assertEqual(dominio.percentil(v, 0.99), 496)
        self.assertEqual(dominio.percentil(v, 0.0), 100)
        self.assertEqual(dominio.percentil(v, 1.0), 500)

    def test_pares_e_impares_y_desordenados(self):
        self.assertEqual(dominio.percentil([4, 1, 3, 2], 0.5), 2)  # (2+3)/2 = 2.5 -> redondea a 2 (banker's) como round()
        self.assertEqual(dominio.percentil([5, 1], 0.5), 3)

    def test_vacio_uno_y_nulos(self):
        self.assertIsNone(dominio.percentil([], 0.5))
        self.assertIsNone(dominio.percentil([None, None], 0.5))
        self.assertEqual(dominio.percentil([42], 0.95), 42)
        self.assertEqual(dominio.percentil([None, 10, 20], 0.5), 15)


class Badge(unittest.TestCase):
    def test_inyeccion_de_codigo_escapada(self):
        for ataque in ['<script>alert(1)</script>', '"><svg onload=alert(1)>', "'; DROP TABLE x;--", '</text><script>x</script>', '&lt;']:
            svg = dominio.construir_badge(ataque, "up")
            self.assertNotIn("<script", svg.lower())
            self.assertNotIn("<svg onload", svg.lower())
            self.assertEqual(svg.count("<svg"), 1, ataque)
            self.assertEqual(svg.count("</svg>"), 1)

    def test_comillas_no_rompen_el_atributo(self):
        svg = dominio.construir_badge('a" onmouseover="x', "up")
        self.assertNotIn('" onmouseover="', svg)
        self.assertIn("&quot;", svg)

    def test_estados_y_colores(self):
        self.assertIn("operativo", dominio.construir_badge("X", "up"))
        self.assertIn("degradado", dominio.construir_badge("X", "degraded"))
        self.assertIn("caído", dominio.construir_badge("X", "down"))
        self.assertIn("sin datos", dominio.construir_badge("X", None))
        self.assertIn("sin datos", dominio.construir_badge("X", "inventado"))

    def test_nombre_largo_se_recorta_y_ancho_es_coherente(self):
        svg = dominio.construir_badge("N" * 100, "up")
        self.assertIn("…", svg)
        import re
        ancho = int(re.search(r'width="(\d+)"', svg).group(1))
        self.assertLess(ancho, 400)

    def test_es_xml_bien_formado(self):
        import xml.etree.ElementTree as ET
        for nombre in ["Normal", "Con & ampersand", "Con <menor>", 'Con "comillas"', "Ñandú ✓"]:
            ET.fromstring(dominio.construir_badge(nombre, "degraded"))  # lanza si el XML está roto


if __name__ == "__main__":
    unittest.main()

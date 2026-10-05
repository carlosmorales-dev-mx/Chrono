"""Pruebas de la espera de la base de datos (con reloj y pausas falsos: no esperan de verdad)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import espera_db  # noqa: E402


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


class Esperar(unittest.TestCase):
    def test_responde_a_la_primera(self):
        r = Reloj()
        self.assertTrue(espera_db.esperar(lambda: None, 60, 1, r, r.dormir))
        self.assertEqual(r.t, 0)

    def test_reintenta_hasta_que_responde(self):
        r, intentos = Reloj(), []

        def intentar():
            intentos.append(r.t)
            if len(intentos) < 4:
                raise ConnectionError("todavía no")
        self.assertTrue(espera_db.esperar(intentar, 60, 2, r, r.dormir))
        self.assertEqual(intentos, [0, 2, 4, 6])

    def test_se_rinde_al_pasar_el_limite_y_dice_por_que(self):
        r = Reloj()

        def intentar():
            raise ConnectionError("conexión rechazada")
        with self.assertRaises(TimeoutError) as cm:
            espera_db.esperar(intentar, 10, 3, r, r.dormir)
        self.assertIn("10 s", str(cm.exception))
        self.assertIn("conexión rechazada", str(cm.exception))
        self.assertLessEqual(r.t, 13)

    def test_cualquier_tipo_de_error_cuenta_como_todavia_no(self):
        r, n = Reloj(), []

        def intentar():
            n.append(1)
            if len(n) == 1:
                raise RuntimeError("falta DATABASE_URL todavía")
        self.assertTrue(espera_db.esperar(intentar, 5, 1, r, r.dormir))


if __name__ == "__main__":
    unittest.main()

"""Pruebas del arranque del contenedor (backend/espera_db.py): la orden que se ejecuta y la respuesta a SIGTERM.
Las últimas dos usan procesos reales (no simulaciones): el comportamiento de las señales no se puede falsear."""
import os
import signal
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import espera_db  # noqa: E402

RAIZ = str(Path(__file__).resolve().parent.parent)


class Principal(unittest.TestCase):
    def llamar(self, argv, fallo=None):
        llamadas = {}

        def esperar_fn(intentar, limite):
            llamadas["limite"] = limite
            if fallo:
                raise fallo
            return True

        def ejecutar(archivo, orden):
            llamadas["exec"] = (archivo, orden)

        codigo = espera_db.principal(argv, intentar=lambda: None, ejecutar=ejecutar, esperar_fn=esperar_fn)
        return codigo, llamadas

    def test_sin_argumentos_espera_60_s_y_no_ejecuta_nada(self):
        codigo, ll = self.llamar([])
        self.assertEqual((codigo, ll["limite"], "exec" in ll), (0, 60.0, False))

    def test_solo_el_limite(self):
        codigo, ll = self.llamar(["15"])
        self.assertEqual((codigo, ll["limite"], "exec" in ll), (0, 15.0, False))

    def test_con_orden_la_ejecuta_tal_cual_despues_de_esperar(self):
        codigo, ll = self.llamar(["60", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"])
        self.assertEqual(ll["limite"], 60.0)
        self.assertEqual(ll["exec"], ("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]))
        self.assertEqual(codigo, 0)

    def test_si_la_base_no_responde_no_ejecuta_la_orden_y_falla(self):
        codigo, ll = self.llamar(["5", "--", "uvicorn", "main:app"], fallo=TimeoutError("no respondió"))
        self.assertEqual(codigo, 1)
        self.assertNotIn("exec", ll)

    def test_limite_que_no_es_numero(self):
        codigo, ll = self.llamar(["mucho", "--", "uvicorn"])
        self.assertEqual(codigo, 2)
        self.assertNotIn("exec", ll)

    def test_una_orden_con_dos_guiones_propios_se_conserva(self):
        _, ll = self.llamar(["1", "--", "python", "-c", "print(1)", "--", "x"])
        self.assertEqual(ll["exec"][1], ["python", "-c", "print(1)", "--", "x"])


@unittest.skipUnless(hasattr(signal, "SIGTERM") and os.name == "posix", "requiere señales POSIX")
class ConProcesosReales(unittest.TestCase):
    def test_sigterm_mientras_espera_termina_al_instante_con_143(self):
        # Un intento que siempre falla = «la base todavía no está lista».
        codigo = textwrap.dedent("""
            import sys; sys.path.insert(0, %r)
            import espera_db
            espera_db.instalar_senales()
            print("esperando", flush=True)
            sys.exit(espera_db.principal(["30"], intentar=lambda: 1 / 0))
        """ % RAIZ)
        p = subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True)
        self.assertEqual(p.stdout.readline().strip(), "esperando")
        time.sleep(0.3)
        inicio = time.monotonic()
        p.send_signal(signal.SIGTERM)
        try:
            salida = p.wait(timeout=5)
        finally:
            if p.poll() is None:
                p.kill()
            p.stdout.close()
        self.assertEqual(salida, 143)
        self.assertLess(time.monotonic() - inicio, 3, "debía detenerse de inmediato, no esperar al final del plazo")

    def test_cuando_la_base_responde_se_reemplaza_por_la_orden_con_el_mismo_pid(self):
        # «exec» no crea un proceso nuevo: el PID de antes y el de la orden deben ser el mismo (así no queda intermediario).
        codigo = textwrap.dedent("""
            import os, sys; sys.path.insert(0, %r)
            import espera_db
            print("ANTES", os.getpid(), flush=True)
            espera_db.principal(["5", "--", sys.executable, "-c", "import os; print('DESPUES', os.getpid())"], intentar=lambda: None)
        """ % RAIZ)
        p = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        lineas = p.stdout.split("\n")
        self.assertIn("base de datos lista", lineas)
        antes = next(l for l in lineas if l.startswith("ANTES ")).split()[1]
        despues = next(l for l in lineas if l.startswith("DESPUES ")).split()[1]
        self.assertEqual(antes, despues)

    def test_la_orden_reemplazada_hereda_el_pid_y_recibe_sigterm_por_su_cuenta(self):
        # Tras el exec el proceso es el de la orden (aquí un «sleep» en Python): SIGTERM lo mata con su acción normal.
        codigo = textwrap.dedent("""
            import sys; sys.path.insert(0, %r)
            import espera_db
            espera_db.instalar_senales()
            espera_db.principal(["5", "--", sys.executable, "-c", "import time; print('listo', flush=True); time.sleep(30)"], intentar=lambda: None)
        """ % RAIZ)
        p = subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True)
        try:
            lineas = []
            while "listo" not in lineas:
                lineas.append(p.stdout.readline().strip())
                self.assertLess(len(lineas), 10)
            p.send_signal(signal.SIGTERM)
            salida = p.wait(timeout=5)
        finally:
            if p.poll() is None:
                p.kill()
            p.stdout.close()
        self.assertEqual(salida, -signal.SIGTERM, "tras el exec debe valer la acción por defecto de SIGTERM, no el manejador de espera_db")


if __name__ == "__main__":
    unittest.main()

"""Pruebas de la configuración (backend/config.py)."""
import importlib
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402


class NormalizarUrlBd(unittest.TestCase):
    def test_pide_psycopg2_de_forma_explicita(self):
        self.assertEqual(config.normalizar_url_bd("postgresql://u:p@db:5432/x"), "postgresql+psycopg2://u:p@db:5432/x")

    def test_acepta_el_prefijo_antiguo_postgres(self):
        self.assertEqual(config.normalizar_url_bd("postgres://u:p@h/x"), "postgresql+psycopg2://u:p@h/x")

    def test_respeta_un_driver_ya_elegido(self):
        for url in ["postgresql+psycopg2://u:p@h/x", "postgresql+psycopg://u:p@h/x", "postgresql+asyncpg://u:p@h/x", "sqlite:///datos.db"]:
            self.assertEqual(config.normalizar_url_bd(url), url)

    def test_conserva_clave_con_simbolos_y_parametros(self):
        url = "postgresql://usuario:p%40ss:w0rd@host.ejemplo.com:5433/mi_bd?sslmode=require&connect_timeout=5"
        self.assertEqual(config.normalizar_url_bd(url), "postgresql+psycopg2://usuario:p%40ss:w0rd@host.ejemplo.com:5433/mi_bd?sslmode=require&connect_timeout=5")

    def test_vacio_y_none_no_revientan(self):
        self.assertIsNone(config.normalizar_url_bd(None))
        self.assertEqual(config.normalizar_url_bd(""), "")

    def test_no_toca_textos_que_solo_contienen_la_palabra(self):
        self.assertEqual(config.normalizar_url_bd("mysql://u@h/postgresql://"), "mysql://u@h/postgresql://")


class DatabaseUrlDesdeElEntorno(unittest.TestCase):
    def recargar(self, valor):
        anterior = os.environ.get("DATABASE_URL")
        try:
            if valor is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = valor
            return importlib.reload(config).DATABASE_URL
        finally:
            if anterior is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = anterior
            importlib.reload(config)

    def test_la_variable_de_entorno_sale_normalizada(self):
        self.assertEqual(self.recargar("postgresql://pulse:pulse@db:5432/pulse"), "postgresql+psycopg2://pulse:pulse@db:5432/pulse")

    def test_sin_variable_queda_en_none(self):
        # (si hay un backend/.env, load_dotenv() la define: en ese caso no se puede probar el caso «sin variable»)
        if (Path(config.__file__).parent / ".env").exists():
            self.skipTest("hay un backend/.env que define DATABASE_URL")
        self.assertIsNone(self.recargar(None))


if __name__ == "__main__":
    unittest.main()

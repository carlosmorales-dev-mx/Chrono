"""Pruebas de las migraciones que NO necesitan Alembic ni PostgreSQL: leen los archivos como texto/AST.

Vigilan lo que más se rompe con el tiempo: que la cadena de versiones esté bien enlazada, que el modo simple
(migrar.py) y la migración 0002 digan lo mismo, y que la migración inicial siga creando los mismos índices que
declaran los modelos. (La prueba contra una base real la hace «alembic upgrade head» en el CI y en fase3.sh.)
"""
import ast
import re
import sqlite3
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERSIONES = RAIZ / "migrations" / "versions"
sys.path.insert(0, str(RAIZ))


def asignaciones(ruta):
    """{nombre: valor} de las asignaciones simples de nivel superior que son literales."""
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"), str(ruta))
    salida = {}
    for n in arbol.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                salida[n.targets[0].id] = ast.literal_eval(n.value)
            except ValueError:
                pass
    return salida


def funciones(ruta):
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"), str(ruta))
    return {n.name for n in arbol.body if isinstance(n, ast.FunctionDef)}


def normalizar(sql):
    return re.sub(r"\s+", " ", sql).strip()


class CadenaDeVersiones(unittest.TestCase):
    def setUp(self):
        self.archivos = sorted(p for p in VERSIONES.glob("*.py") if p.name != "__init__.py")

    def test_hay_migraciones(self):
        self.assertGreaterEqual(len(self.archivos), 2)

    def test_cada_migracion_esta_completa(self):
        for p in self.archivos:
            datos = asignaciones(p)
            self.assertIn("revision", datos, p.name)
            self.assertIn("down_revision", datos, p.name)
            self.assertTrue(p.name.startswith(datos["revision"] + "_"), f"{p.name}: el nombre debe empezar por su revisión")
            self.assertLessEqual({"upgrade", "downgrade"}, funciones(p), f"{p.name} necesita upgrade() y downgrade()")

    def test_la_cadena_es_lineal_con_una_sola_cabeza(self):
        hijos, raices, ids = {}, [], []
        for p in self.archivos:
            d = asignaciones(p)
            ids.append(d["revision"])
            if d["down_revision"] is None:
                raices.append(d["revision"])
            else:
                self.assertNotIn(d["down_revision"], hijos, f"dos migraciones parten de {d['down_revision']}: hay una bifurcación")
                hijos[d["down_revision"]] = d["revision"]
        self.assertEqual(len(ids), len(set(ids)), "hay identificadores de revisión repetidos")
        self.assertEqual(len(raices), 1, "debe haber exactamente una migración inicial")
        actual, recorrido = raices[0], [raices[0]]
        while actual in hijos:
            actual = hijos[actual]
            recorrido.append(actual)
        self.assertEqual(sorted(recorrido), sorted(ids), "alguna migración no está enlazada a la cadena")


class ModoSimpleYAlembicDicenLoMismo(unittest.TestCase):
    def test_sentencias_iguales(self):
        simple = [normalizar(s) for s in asignaciones(RAIZ / "migrar.py")["SENTENCIAS"]]
        alembic_0002 = [normalizar(s) for s in asignaciones(next(VERSIONES.glob("0002_*.py")))["SENTENCIAS"]]
        self.assertEqual(simple, alembic_0002, "migrar.py (modo simple) y la migración 0002 deben ser idénticos: actualiza los dos")


class MigracionInicialYModelos(unittest.TestCase):
    def indices_del_modelo(self):
        """ix_<tabla>_<columna> por cada Column(..., index=True) de db_models.py."""
        arbol = ast.parse((RAIZ / "db_models.py").read_text(encoding="utf-8"))
        esperados = set()
        for clase in (n for n in arbol.body if isinstance(n, ast.ClassDef)):
            tabla = None
            for n in clase.body:
                if isinstance(n, ast.Assign) and n.targets[0].id == "__tablename__":
                    tabla = ast.literal_eval(n.value)
            for n in clase.body:
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", "") == "Column":
                    if any(k.arg == "index" and getattr(k.value, "value", False) is True for k in n.value.keywords):
                        esperados.add(f"ix_{tabla}_{n.targets[0].id}")
        return esperados

    def test_la_migracion_inicial_crea_los_indices_que_declara_el_modelo(self):
        sentencias = asignaciones(next(VERSIONES.glob("0001_*.py")))["INDICES"]
        creados = {re.search(r"INDEX IF NOT EXISTS (\w+)", s).group(1) for s in sentencias}
        self.assertEqual(self.indices_del_modelo(), creados, "db_models.py y la migración 0001 declaran índices distintos")

    def test_los_indices_de_table_args_estan_en_la_0002(self):
        modelo = (RAIZ / "db_models.py").read_text(encoding="utf-8")
        sql_0002 = " ".join(asignaciones(next(VERSIONES.glob("0002_*.py")))["SENTENCIAS"])
        for nombre in re.findall(r'Index\(\s*"(\w+)"', modelo):
            self.assertIn(nombre, sql_0002, f"el índice {nombre} del modelo no lo crea ninguna migración")


class SqlDeLaMigracion0002(unittest.TestCase):
    """Ejecuta el SQL real de la 0002 sobre SQLite (admite índices parciales) para comprobar su lógica."""

    def conexion(self):
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE chequeos (id INTEGER PRIMARY KEY, servicio_id INT, creado_en TIMESTAMP)")
        c.execute("CREATE TABLE incidentes (id INTEGER PRIMARY KEY, servicio_id INT NOT NULL, estado TEXT, inicio TIMESTAMP, fin TIMESTAMP)")
        return c

    def aplicar(self, c):
        for s in asignaciones(next(VERSIONES.glob("0002_*.py")))["SENTENCIAS"]:
            c.execute(s.replace("now()", "CURRENT_TIMESTAMP"))  # now() es de PostgreSQL

    def test_cierra_los_duplicados_conservando_el_mas_antiguo_y_crea_el_indice(self):
        c = self.conexion()
        c.executemany("INSERT INTO incidentes (id, servicio_id, estado, fin) VALUES (?,?,?,NULL)", [(1, 7, "down"), (2, 7, "down"), (3, 7, "degraded"), (4, 8, "down")])
        self.aplicar(c)
        abiertos = c.execute("SELECT id FROM incidentes WHERE fin IS NULL ORDER BY id").fetchall()
        self.assertEqual(abiertos, [(1,), (4,)])  # un abierto por servicio: el más antiguo de cada uno

    def test_el_indice_impide_un_segundo_incidente_abierto(self):
        c = self.conexion()
        self.aplicar(c)
        c.execute("INSERT INTO incidentes (servicio_id, estado, fin) VALUES (1, 'down', NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("INSERT INTO incidentes (servicio_id, estado, fin) VALUES (1, 'degraded', NULL)")
        c.execute("INSERT INTO incidentes (servicio_id, estado, fin) VALUES (2, 'down', NULL)")  # otro servicio: sí
        c.execute("UPDATE incidentes SET fin = CURRENT_TIMESTAMP WHERE servicio_id = 1")
        c.execute("INSERT INTO incidentes (servicio_id, estado, fin) VALUES (1, 'down', NULL)")  # cerrado el anterior: sí

    def test_es_idempotente(self):
        c = self.conexion()
        c.execute("INSERT INTO incidentes (servicio_id, estado, fin) VALUES (1, 'down', NULL)")
        self.aplicar(c)
        self.aplicar(c)  # IF NOT EXISTS: la segunda vez no falla ni cambia nada
        self.assertEqual(c.execute("SELECT COUNT(*) FROM incidentes WHERE fin IS NULL").fetchone(), (1,))

    def test_indices_de_la_0001_se_pueden_crear_dos_veces(self):
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE servicios (id INT)")
        c.execute("CREATE TABLE chequeos (id INT, servicio_id INT, creado_en TIMESTAMP)")
        c.execute("CREATE TABLE incidentes (id INT, servicio_id INT)")
        for _ in range(2):
            for s in asignaciones(next(VERSIONES.glob("0001_*.py")))["INDICES"]:
                c.execute(s)


if __name__ == "__main__":
    unittest.main()

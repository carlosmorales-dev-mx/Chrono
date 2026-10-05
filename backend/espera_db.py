"""Espera a que la base de datos acepte conexiones. Lo usa el contenedor del backend antes de arrancar,
porque PostgreSQL puede tardar unos segundos en estar listo (y compose no siempre espera a que lo esté).

    python espera_db.py [segundos]      (60 por defecto; termina con código 1 si no responde a tiempo)
"""
import sys
import time


def esperar(intentar, limite_s=60.0, pausa_s=1.0, reloj=time.monotonic, dormir=time.sleep):
    """Llama a `intentar()` hasta que no lance ninguna excepción. Lanza TimeoutError si se acaba el tiempo."""
    inicio = reloj()
    ultimo = None
    while True:
        try:
            intentar()
            return True
        except Exception as e:  # noqa: BLE001  (cualquier fallo de conexión cuenta como «todavía no»)
            ultimo = e
        if reloj() - inicio >= limite_s:
            raise TimeoutError(f"la base de datos no respondió en {limite_s:.0f} s: {ultimo}")
        dormir(pausa_s)


def _intentar():
    from sqlalchemy import text

    from database import engine

    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))


if __name__ == "__main__":
    limite = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    try:
        esperar(_intentar, limite)
    except TimeoutError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print("base de datos lista")

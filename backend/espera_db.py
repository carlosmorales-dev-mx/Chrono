"""Espera a que la base de datos acepte conexiones. Lo usa el contenedor del backend antes de arrancar,
porque PostgreSQL puede tardar unos segundos en estar listo (y compose no siempre espera a que lo esté).

    python espera_db.py [segundos]                    espera y termina (código 1 si no responde a tiempo; 60 s por defecto)
    python espera_db.py [segundos] -- ORDEN ARGS…     espera y, cuando la base responde, SE REEMPLAZA por ORDEN (como «exec»)

La segunda forma es la del contenedor. Así este proceso es el principal mientras espera, atiende SIGTERM (el contenedor
se detiene al instante en vez de tardar 10 s) y después pasa a ser uvicorn sin dejar ningún intermediario.
"""
import os
import signal
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


def _terminar(numero, _marco):
    sys.exit(128 + numero)  # convención de shell: 143 para SIGTERM


def instalar_senales():
    """El proceso 1 de un contenedor ignora SIGTERM salvo que tenga un manejador propio: aquí se lo ponemos."""
    signal.signal(signal.SIGTERM, _terminar)


def principal(argv, intentar=_intentar, ejecutar=os.execvp, esperar_fn=esperar):
    args = list(argv)
    orden = []
    if "--" in args:
        corte = args.index("--")
        orden, args = args[corte + 1:], args[:corte]
    try:
        limite = float(args[0]) if args else 60.0
    except ValueError:
        print(f"el tiempo límite debe ser un número de segundos, no {args[0]!r}", file=sys.stderr)
        return 2
    try:
        esperar_fn(intentar, limite)
    except TimeoutError as e:
        print(e, file=sys.stderr)
        return 1
    print("base de datos lista", flush=True)
    if orden:
        # Python deja SIGPIPE ignorado y los procesos hijos lo heredan; se restablece para que uvicorn arranque «limpio».
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        ejecutar(orden[0], orden)
    return 0


if __name__ == "__main__":
    instalar_senales()
    sys.exit(principal(sys.argv[1:]))

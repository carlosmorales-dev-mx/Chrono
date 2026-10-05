#!/usr/bin/env python3
"""Prueba de humo del backend EN VIVO (solo biblioteca estándar).

    python tools/humo_backend.py http://127.0.0.1:8001 [--token TOKEN] [--abrir 2] [--cerrar 3]

Recorre los endpoints con peticiones reales. Crea UN servicio temporal («__humo__…») para probar el ingest,
los incidentes y la insignia, y lo borra al terminar (aunque algo falle). No toca tus servicios.
Termina con código 0 si todo pasó y 1 si algo falló.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid

fallas = []


def chequear(descripcion, condicion, detalle=""):
    print(("  ok    " if condicion else "  FALLA ") + descripcion + ("" if condicion or not detalle else f"  ({detalle})"))
    if not condicion:
        fallas.append(descripcion)
    return condicion


class Cliente:
    def __init__(self, base, token):
        self.base, self.token = base.rstrip("/"), token

    def pedir(self, metodo, ruta, cuerpo=None, con_token=False):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        cabeceras = {"Content-Type": "application/json"} if datos else {}
        if con_token and self.token:
            cabeceras["X-Ingest-Token"] = self.token
        req = urllib.request.Request(self.base + ruta, data=datos, method=metodo, headers=cabeceras)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf-8", "replace")

    def json(self, metodo, ruta, cuerpo=None, con_token=False):
        estado, cab, texto = self.pedir(metodo, ruta, cuerpo, con_token)
        try:
            return estado, cab, json.loads(texto) if texto else None
        except ValueError:
            return estado, cab, texto


def correr(base, token, abrir, cerrar):
    c = Cliente(base, token)
    cab = lambda d, k: {kk.lower(): v for kk, v in d.items()}.get(k.lower())  # noqa: E731

    print("\n[1] Lecturas")
    e, _, d = c.json("GET", "/health")
    chequear("GET /health responde 200 y la base contesta", e == 200 and isinstance(d, dict) and d.get("db") == "ok", f"{e} {d}")
    e, _, d = c.json("GET", "/servicios")
    chequear("GET /servicios devuelve una lista", e == 200 and isinstance(d, list), str(e))
    e, _, d = c.json("GET", "/chequeos/estado-actual")
    chequear("GET /chequeos/estado-actual devuelve una lista", e == 200 and isinstance(d, list), str(e))
    e, h, d = c.json("GET", "/incidentes")
    total = cab(h, "x-total-count")
    chequear("GET /incidentes devuelve una lista con X-Total-Count numérico", e == 200 and isinstance(d, list) and str(total).isdigit(), f"{e} total={total}")
    e, _, _ = c.json("GET", "/incidentes?estado=zzz")
    chequear("GET /incidentes?estado=zzz se rechaza con 422", e == 422, str(e))
    e, _, _ = c.json("GET", "/incidentes?dias=0")
    chequear("GET /incidentes?dias=0 se rechaza con 422 (validación de parámetros)", e == 422, str(e))

    print("\n[2] Seguridad")
    ingest = {"resultados": [{"servicio_id": 999999, "estado": "up", "codigo": 200, "latencia_ms": 10}]}
    if token:
        e, _, _ = c.json("POST", "/internal/ingest", ingest, con_token=False)
        chequear("el ingest SIN token se rechaza (401)", e == 401, str(e))
        mal = Cliente(base, "token-equivocado")
        e, _, _ = mal.json("POST", "/internal/ingest", ingest, con_token=True)
        chequear("el ingest con token EQUIVOCADO se rechaza (401)", e == 401, str(e))
    else:
        print("  (INGEST_TOKEN no está definido: se omite la prueba de rechazo)")
    e, _, d = c.json("POST", "/internal/ingest", ingest, con_token=True)
    chequear("un servicio inexistente se ignora SIN perder el lote (guardados 0, ignorados 1)", e == 201 and d == {"guardados": 0, "ignorados": 1}, f"{e} {d}")
    e, _, _ = c.json("POST", "/internal/ingest", {"resultados": []}, con_token=True)
    chequear("un lote vacío se rechaza (422)", e == 422, str(e))
    e, _, _ = c.json("POST", "/internal/ingest", {"resultados": [{"servicio_id": 1, "estado": "raro"}]}, con_token=True)
    chequear("un estado inventado se rechaza (422)", e == 422, str(e))
    for url in ["file:///etc/passwd", "javascript:alert(1)", "http://127.0.0.1:8001", "http://169.254.169.254/latest/meta-data/", "ftp://example.com", "https://user:clave@example.com"]:
        e, _, _ = c.json("POST", "/servicios", {"nombre": "__humo__ malo", "url": url})
        chequear(f"crear un servicio con URL {url[:44]} se rechaza", e in (422, 403), str(e))

    print("\n[3] Ciclo de vida de un servicio temporal")
    sufijo = uuid.uuid4().hex[:10]
    url = f"https://example.com/chrono-humo-{sufijo}"
    nombre = f"__humo__ <script>alert({sufijo})</script>"
    e, _, d = c.json("POST", "/servicios", {"nombre": nombre, "url": url})
    if e == 403:
        print("  (el servidor está en modo de solo lectura: se omite esta parte)")
        return
    if not chequear("POST /servicios crea el servicio (201)", e == 201 and isinstance(d, dict) and "id" in d, f"{e} {d}"):
        return
    sid = d["id"]
    try:
        chequear("el nombre se guarda tal cual (sin alterarlo)", d["nombre"] == nombre)
        e, _, _ = c.json("POST", "/servicios", {"nombre": "otro", "url": url.upper().replace("HTTPS", "https")})
        chequear("la misma URL otra vez se rechaza (409)", e == 409, str(e))

        e, h, svg = c.pedir("GET", f"/badge/{sid}.svg")
        chequear("GET /badge devuelve un SVG", e == 200 and "image/svg+xml" in (cab(h, "content-type") or ""), f"{e}")
        chequear("la insignia NO contiene el <script> del nombre (está escapado)", "<script" not in svg.lower() and "&lt;script&gt;" in svg)
        chequear("la insignia manda una Content-Security-Policy", "default-src 'none'" in (cab(h, "content-security-policy") or ""))

        e, _, d = c.json("PUT", f"/servicios/{sid}", {"nombre": f"__humo__ editado {sufijo}", "url": url})
        chequear("PUT /servicios/{id} edita el servicio", e == 200 and d["nombre"].startswith("__humo__ editado"), f"{e}")

        def ingerir(estado, lat=None, codigo=None):
            return c.json("POST", "/internal/ingest", {"resultados": [{"servicio_id": sid, "estado": estado, "codigo": codigo, "latencia_ms": lat}]}, con_token=True)

        def incidentes(extra=""):
            return c.json("GET", f"/incidentes?servicio_id={sid}{extra}")[2]

        print("\n[4] Incidentes con histéresis (abrir tras %d chequeos malos, cerrar tras %d buenos)" % (abrir, cerrar))
        e, _, d = ingerir("up", 50, 200)
        chequear("el ingest guarda el chequeo (201, guardados 1)", e == 201 and d == {"guardados": 1, "ignorados": 0}, f"{e} {d}")
        chequear("un servicio sano no tiene incidentes", incidentes() == [])
        total_ingests = 1
        for i in range(1, abrir):
            ingerir("down")
            total_ingests += 1
            chequear(f"tras {i} chequeo(s) malo(s) todavía NO hay incidente", incidentes() == [], str(incidentes()))
        ingerir("down")
        total_ingests += 1
        abiertos = incidentes("&activos=true")
        chequear(f"al llegar a {abrir} chequeos malos seguidos se abre UN incidente", len(abiertos) == 1 and abiertos[0]["estado"] == "down" and abiertos[0]["activo"] and abiertos[0]["servicio_id"] == sid, str(abiertos))
        ingerir("down")
        total_ingests += 1
        chequear("más chequeos malos no abren otro incidente", len(incidentes()) == 1)
        for i in range(1, cerrar):
            ingerir("up", 50, 200)
            total_ingests += 1
            chequear(f"tras {i} chequeo(s) bueno(s) el incidente SIGUE abierto", len(incidentes("&activos=true")) == 1)
        ingerir("up", 50, 200)
        total_ingests += 1
        todos = incidentes()
        chequear(f"tras {cerrar} chequeos buenos seguidos el incidente se cierra", len(todos) == 1 and not todos[0]["activo"] and todos[0]["fin"] is not None and todos[0]["duracion_seg"] >= 0, str(todos))

        print("\n[5] Historial y percentiles")
        e, _, hist = c.json("GET", f"/chequeos/{sid}/historial")
        chequear("el historial devuelve tramos con estado y número de chequeos", e == 200 and isinstance(hist, list) and hist and all({"creado_en", "latencia_ms", "estado", "n"} <= set(p) for p in hist), str(hist)[:120])
        chequear("el historial INCLUYE la caída (algún tramo con estado down)", any(p["estado"] == "down" for p in hist))
        chequear("ningún chequeo se pierde al agrupar", sum(p["n"] for p in hist) == total_ingests, f"{sum(p['n'] for p in hist)} de {total_ingests}")
        e, _, pc = c.json("GET", f"/chequeos/{sid}/percentiles")
        chequear("percentiles devuelve p50/p95/p99", e == 200 and set(pc) == {"p50", "p95", "p99"} and pc["p50"] == 50, str(pc))
        e, _, _ = c.json("GET", f"/chequeos/{sid}/historial?horas=0")
        chequear("historial?horas=0 se rechaza (422)", e == 422, str(e))
    finally:
        e, _, _ = c.json("DELETE", f"/servicios/{sid}")
        chequear("DELETE /servicios/{id} limpia el servicio temporal (204)", e == 204, str(e))
        e, _, _ = c.json("DELETE", f"/servicios/{sid}")
        chequear("borrarlo otra vez da 404", e == 404, str(e))
        e, _, _ = c.pedir("GET", f"/badge/{sid}.svg")
        chequear("su insignia ya no existe (404)", e == 404, str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--token", default=None)
    ap.add_argument("--abrir", type=int, default=2)
    ap.add_argument("--cerrar", type=int, default=3)
    a = ap.parse_args()
    try:
        correr(a.base, a.token, a.abrir, a.cerrar)
    except Exception as e:  # una excepción inesperada también es una falla
        print(f"  FALLA excepción inesperada: {e!r}")
        fallas.append(repr(e))
    print(f"\nRESULTADO: {'TODO BIEN' if not fallas else str(len(fallas)) + ' falla(s)'}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())

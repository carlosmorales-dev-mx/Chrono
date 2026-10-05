#!/usr/bin/env python3
"""Comprueba que el README dice la verdad: lo documentado existe y lo que existe está documentado.

    python tools/verificar_docs.py [RAIZ]

Cruza README.md y README.es.md con el código:
  · enlaces e imágenes relativos y rutas de archivo entre `comillas` → existen
  · «make algo» → es un objetivo del Makefile
  · tablas de variables de entorno (| `VARIABLE` | …) ↔ los .env.example y el código: ni sobra ni falta ninguna
  · tabla de endpoints (| GET | `/ruta` | …) ↔ las rutas de FastAPI: ni sobra ni falta ninguna
  · los dos idiomas documentan exactamente lo mismo
Termina con código 1 si algo no coincide. Solo biblioteca estándar.
"""
import os
import re
import sys

RAIZ = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
IDIOMAS = ["README.md", "README.es.md"]
errores, comprobaciones = [], 0


def ruta(*p):
    return os.path.join(RAIZ, *p)


def leer(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def err(m):
    errores.append(m)
    print("  ✗", m)


def ok(m):
    global comprobaciones
    comprobaciones += 1
    print("  ✓", m)


# ------------------------------------------------------------------ lo que EXISTE en el código
def objetivos_make():
    return set(re.findall(r"^([A-Za-z0-9_-]+):(?!=)", leer(ruta("Makefile")), flags=re.M))


def variables_en_codigo():
    """Variables de entorno que el proyecto lee: .env.example, os.getenv(...), config.py y compose."""
    nombres = set()
    for ejemplo in ("backend/.env.example", "worker/.env.example"):
        nombres |= set(re.findall(r"^\s*#?\s*([A-Z][A-Z0-9_]{2,})=", leer(ruta(ejemplo)), flags=re.M))
    return nombres


def variables_de_ejemplo():
    """{archivo: variables} solo de los .env.example (lo que el README debe documentar)."""
    salida = {}
    for ejemplo in ("backend/.env.example", "worker/.env.example"):
        salida[ejemplo] = set(re.findall(r"^\s*#?\s*([A-Z][A-Z0-9_]{2,})=", leer(ruta(ejemplo)), flags=re.M))
    return salida


def variables_leidas_por_el_codigo():
    nombres = set()
    for archivo in ("backend/config.py", "worker/check_servicios.py", "frontend/src/config.js"):
        t = leer(ruta(archivo))
        nombres |= set(re.findall(r"""(?:_texto|_booleano|_entero|_numero|getenv|environ\.get|get)\(\s*["']([A-Z][A-Z0-9_]+)["']""", t))
        nombres |= set(re.findall(r"env\.(VITE_[A-Z_]+)", t))
    nombres |= {v for v in re.findall(r"\$\{([A-Z][A-Z0-9_]+)", leer(ruta("podman-compose.stack.yml")))}
    return nombres


def endpoints_en_codigo():
    rutas = set()
    for archivo in ("backend/api/routes.py", "backend/main.py"):
        for metodo, path in re.findall(r"""@(?:router|app)\.(get|post|put|patch|delete|websocket)\(\s*["']([^"']+)["']""", leer(ruta(archivo))):
            rutas.add((metodo.upper() if metodo != "websocket" else "WS", re.sub(r"\{\w+\}", "{id}", path)))
    return rutas


# ------------------------------------------------------------------ lo que DICE el README
METODOS = {"GET", "POST", "PUT", "PATCH", "DELETE", "WS"}


def tablas_variables(texto):
    """Variables de las tablas de configuración (la primera columna entre `comillas`); la tabla de la API usa métodos."""
    return set(re.findall(r"^\|\s*`([A-Z][A-Z0-9_]{2,})`\s*\|", texto, flags=re.M)) - METODOS


def tabla_endpoints(texto):
    salida = set()
    for metodo, path in re.findall(r"^\|\s*`?(GET|POST|PUT|PATCH|DELETE|WS)`?\s*\|\s*`([^`]+)`\s*\|", texto, flags=re.M):
        salida.add((metodo, re.sub(r"\{\w+\}", "{id}", path.split("?")[0])))
    return salida


def make_mencionados(texto):
    # «make dev», «make stack-down», `make test`; ignora «make -n» y frases como «make sure»
    return set(re.findall(r"\bmake\s+([a-z][a-z0-9_-]+)\b", texto)) - {"sure", "a", "it", "the", "your", "this", "that", "sense", "no", "up", "use", "one", "copy", "changes"}


def rutas_mencionadas(texto):
    candidatos = set(re.findall(r"`((?:backend|worker|frontend|tools|docs|\.github)/[\w./-]+\.[a-z]{1,5})`", texto))
    candidatos |= set(re.findall(r"`((?:podman-compose(?:\.stack)?\.yml|Makefile|README(?:\.es)?\.md))`", texto))
    # Los .env están en .gitignore: en un clon limpio solo existe el .env.example, así que no se exigen.
    return {c for c in candidatos if not re.search(r"(^|/)\.env$", c)}


def enlaces_relativos(texto):
    salida = set()
    for destino in re.findall(r"\]\(([^)\s]+)", texto):
        if destino.startswith(("http://", "https://", "#", "mailto:")):
            continue
        salida.add(destino.split("#")[0])
    return {d for d in salida if d}


def main():
    print(f"\nRevisando la documentación de {RAIZ}\n")
    codigo_make, codigo_eps, codigo_vars = objetivos_make(), variables_de_ejemplo(), variables_leidas_por_el_codigo()
    existentes = set().union(*codigo_eps.values()) | codigo_vars
    codigo_rutas = endpoints_en_codigo()
    por_idioma = {}

    for nombre in IDIOMAS:
        texto = leer(ruta(nombre))
        print(f"[{nombre}]")
        if not texto:
            err(f"{nombre}: no existe o está vacío")
            continue
        e0 = len(errores)
        for destino in sorted(enlaces_relativos(texto)):
            if not os.path.exists(ruta(destino)):
                err(f"{nombre}: el enlace o imagen «{destino}» no existe")
        for p in sorted(rutas_mencionadas(texto)):
            if not os.path.exists(ruta(p)):
                err(f"{nombre}: menciona el archivo «{p}», que no existe")
        mk = make_mencionados(texto)
        for m in sorted(mk):
            if m not in codigo_make:
                err(f"{nombre}: menciona «make {m}», que no es un objetivo del Makefile")
        docs_vars = tablas_variables(texto)
        for v in sorted(docs_vars):
            if v not in existentes:
                err(f"{nombre}: documenta la variable «{v}», que ningún .env.example ni el código lee")
        for archivo, vs in codigo_eps.items():
            for v in sorted(vs - docs_vars):
                err(f"{nombre}: la variable «{v}» de {archivo} no está documentada en la tabla de configuración")
        docs_eps = tabla_endpoints(texto)
        for metodo, path in sorted(docs_eps - codigo_rutas):
            err(f"{nombre}: documenta «{metodo} {path}», que no existe en el backend")
        for metodo, path in sorted(codigo_rutas - docs_eps):
            if path != "/internal/ingest":  # interna, no se documenta como API pública
                err(f"{nombre}: el endpoint «{metodo} {path}» existe y no está en la tabla de la API")
        titulos = re.findall(r"^## ", texto, flags=re.M)
        por_idioma[nombre] = {"mk": mk, "vars": docs_vars, "eps": docs_eps, "secciones": len(titulos), "rutas": rutas_mencionadas(texto), "enlaces": enlaces_relativos(texto)}
        if len(errores) == e0:
            ok(f"{nombre}: {len(enlaces_relativos(texto))} enlaces, {len(rutas_mencionadas(texto))} rutas de archivo, {len(mk)} atajos de make, {len(docs_vars)} variables y {len(docs_eps)} endpoints coinciden con el código")

    if len(por_idioma) == 2:
        print("[paridad entre idiomas]")
        a, b = por_idioma[IDIOMAS[0]], por_idioma[IDIOMAS[1]]
        e0 = len(errores)
        for clave, etiqueta in (("mk", "atajos de make"), ("vars", "variables de entorno"), ("eps", "endpoints"), ("rutas", "archivos mencionados"), ("enlaces", "enlaces/imágenes")):
            # el enlace de cambio de idioma (README.md <-> README.es.md) es distinto por diseño
            solo_a, solo_b = a[clave] - b[clave] - set(IDIOMAS), b[clave] - a[clave] - set(IDIOMAS)
            if solo_a:
                err(f"{etiqueta}: solo en {IDIOMAS[0]}: {sorted(solo_a)}")
            if solo_b:
                err(f"{etiqueta}: solo en {IDIOMAS[1]}: {sorted(solo_b)}")
        if a["secciones"] != b["secciones"]:
            err(f"los idiomas tienen distinto número de secciones (##): {a['secciones']} vs {b['secciones']}")
        if len(errores) == e0:
            ok(f"los dos idiomas documentan lo mismo ({a['secciones']} secciones, mismos atajos, variables, endpoints, archivos e imágenes)")

    print(f"\nRESULTADO: {len(errores)} errores, {comprobaciones} grupos de comprobaciones correctos")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

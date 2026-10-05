#!/usr/bin/env python3
"""Mantenimiento del repositorio: archivos sin uso, carpetas vacías y cachés. Solo biblioteca estándar.

    python tools/mantenimiento.py sin-uso            informe de archivos que nada usa
    python tools/mantenimiento.py sin-uso --borrar   ...y ofrece borrar los que son SEGUROS de borrar
    python tools/mantenimiento.py vacias [--borrar]  carpetas vacías
    python tools/mantenimiento.py cache  [--borrar]  cachés regenerables (__pycache__, dist, .pytest_cache…)
    python tools/mantenimiento.py todo               los tres informes, sin borrar nada
    opciones: --raiz RUTA · -y (no preguntar) · --check (código 1 si hay algo SEGURO de borrar; útil en CI)

Cómo decide qué está "sin uso":
  · Frontend: parte de index.html y sigue los imports (también los dinámicos), @import y url() de CSS y
    las rutas de imágenes de las plantillas. Lo que no se alcanza desde ahí, no se usa.
  · Python: parte de los archivos que se ejecutan (con `if __name__ == "__main__"`, nombrados en el Makefile,
    compose o Containerfile, o de pruebas) y sigue los imports.
  · SEGURO = nada lo referencia. REVISAR = señales que requieren juicio (imports sin usar, claves de
    traducción sin uso, dependencias sin importar…); esas NUNCA se borran solas.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile

IGNORAR = {".git", "node_modules", "venv", ".venv", "env", "dist", "build", "__pycache__", ".pytest_cache", ".ruff_cache",
           ".mypy_cache", ".cache", "htmlcov", ".idea", ".vscode", ".claude", ".apply-backups", ".tox", ".nox", "site-packages"}
CACHES = ["__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", ".coverage", ".vite"]
BASURA = re.compile(r"(\.bak|\.orig|\.rej|\.tmp|\.swp|~|\.log)$|^(\.DS_Store|Thumbs\.db|desktop\.ini|nohup\.out)$", re.I)
EXT_JS = (".js", ".mjs", ".ts", ".jsx", ".tsx")
EXT_ACTIVOS = EXT_JS + (".vue", ".css", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".woff", ".woff2", ".ico")
PUBLIC_ESPECIALES = {"robots.txt", "sitemap.xml", "manifest.webmanifest", "manifest.json", "_redirects", "_headers", "cname", ".nojekyll", "404.html", "humans.txt", "security.txt"}

COLOR = sys.stdout.isatty()
def c(codigo, texto): return f"\033[{codigo}m{texto}\033[0m" if COLOR else texto
def negrita(t): return c("1", t)
def verde(t): return c("32", t)
def ambar(t): return c("33", t)


def caminar(raiz):
    for dirpath, dirs, archivos in os.walk(raiz):
        dirs[:] = sorted(d for d in dirs if d not in IGNORAR)
        yield dirpath, dirs, sorted(archivos)


def todos_los_archivos(raiz):
    return [os.path.join(d, a) for d, _, archivos in caminar(raiz) for a in archivos]


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def rel(ruta, raiz):
    return os.path.relpath(ruta, raiz).replace(os.sep, "/")


def tamano(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


# =============================================================================== frontend
def quitar_comentarios_js(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


def especificadores_js(src):
    src = quitar_comentarios_js(src)
    patrones = [r"""\bfrom\s*['"]([^'"]+)['"]""", r"""\bimport\s*['"]([^'"]+)['"]""", r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""",
                r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)""", r"""new\s+URL\(\s*['"]([^'"]+)['"]\s*,\s*import\.meta\.url""",
                r"""\bimport\.meta\.glob\(\s*['"]([^'"]+)['"]"""]
    return {m for p in patrones for m in re.findall(p, src)}


def referencias_css(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    refs = set(re.findall(r"""@import\s+(?:url\()?\s*['"]?([^'")\s;]+)""", src))
    refs |= set(re.findall(r"""url\(\s*['"]?([^'")\s]+)""", src))
    return {r for r in refs if not r.startswith(("data:", "http:", "https:", "#", "//"))}


def referencias_plantilla(src):
    m = re.search(r"<template[^>]*>(.*)</template>", src, flags=re.S)
    if not m:
        return set()
    return set(re.findall(r"""\b(?:src|href|poster)\s*=\s*['"]([^'"{}]+\.(?:svg|png|jpe?g|webp|gif|avif|ico|css|woff2?))['"]""", m.group(1)))


def partes_vue(src):
    scripts = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", src, flags=re.S))
    estilos = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, flags=re.S))
    return scripts, estilos


def resolver_import(spec, desde, src_dir, alias):
    """Convierte un especificador en una ruta de archivo existente, o None (paquete externo o inexistente)."""
    if spec.startswith("@/") and alias:
        base = os.path.join(src_dir, spec[2:])
    elif spec.startswith("/"):
        base = os.path.join(os.path.dirname(src_dir), spec.lstrip("/")) if os.path.exists(os.path.join(os.path.dirname(src_dir), spec.lstrip("/"))) else os.path.join(src_dir, spec.lstrip("/"))
    elif spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(desde), spec))
    else:
        return None
    base = base.split("?")[0].split("#")[0]
    candidatos = [base] + [base + e for e in EXT_ACTIVOS] + [os.path.join(base, "index" + e) for e in EXT_JS + (".vue",)]
    for cand in candidatos:
        if os.path.isfile(cand):
            return os.path.normpath(cand)
    return None


def analizar_frontend(raiz):
    fe = os.path.join(raiz, "frontend")
    if not os.path.isfile(os.path.join(fe, "package.json")):
        return None
    src_dir = os.path.join(fe, "src")
    if not os.path.isdir(src_dir):
        return None
    vite = leer(os.path.join(fe, "vite.config.js")) + leer(os.path.join(fe, "vite.config.ts"))
    alias = "'@'" in vite or '"@"' in vite or "@:" in vite
    index = leer(os.path.join(fe, "index.html"))

    entradas = []
    for ref in re.findall(r"""(?:src|href)\s*=\s*['"]([^'"]+)['"]""", index):
        r = resolver_import(ref if ref.startswith(("/", ".")) else "./" + ref, os.path.join(fe, "index.html"), src_dir, alias)
        if r and r.startswith(src_dir):
            entradas.append(r)

    alcanzados, pendientes, paquetes, textos = set(), list(entradas), set(), {}
    while pendientes:
        f = pendientes.pop()
        if f in alcanzados:
            continue
        alcanzados.add(f)
        src = leer(f)
        scripts, estilos = (partes_vue(src) if f.endswith(".vue") else (src if f.endswith(EXT_JS) else "", src if f.endswith(".css") else ""))
        textos[f] = src
        refs = set()
        if f.endswith(".vue"):
            refs |= especificadores_js(scripts) | referencias_css(estilos) | referencias_plantilla(src)
        elif f.endswith(EXT_JS):
            refs |= especificadores_js(scripts)
        elif f.endswith(".css"):
            refs |= referencias_css(estilos)
        for ref in refs:
            destino = resolver_import(ref, f, src_dir, alias)
            if destino and destino.startswith(os.path.dirname(src_dir)):
                pendientes.append(destino)
            elif destino is None and not ref.startswith((".", "/", "@/")):
                paquetes.add(ref.split("/")[0] if not ref.startswith("@") else "/".join(ref.split("/")[:2]))

    en_src = [f for f in todos_los_archivos(src_dir) if f.endswith(EXT_ACTIVOS)]
    sin_uso = sorted(f for f in en_src if os.path.normpath(f) not in alcanzados)

    # public/: un archivo se usa si su nombre aparece en lo alcanzado, en index.html, en vite.config o en la documentación
    texto_vivo = "\n".join(list(textos.values()) + [index, vite])
    docs = "\n".join(leer(p) for p in todos_los_archivos(raiz) if p.endswith((".md", ".yml", ".yaml")) and "node_modules" not in p)
    publicos = []
    pub = os.path.join(fe, "public")
    if os.path.isdir(pub):
        for f in todos_los_archivos(pub):
            nombre = os.path.basename(f)
            if nombre.lower() in PUBLIC_ESPECIALES:
                continue
            if nombre not in texto_vivo and nombre not in docs:
                publicos.append(f)

    # claves de traducción sin uso
    claves_sin_uso = []
    loc_dir = os.path.join(src_dir, "locales")
    if os.path.isdir(loc_dir):
        usadas_texto = "\n".join(textos.values())
        llamadas = []
        for m in re.finditer(r"(?<![\w$.])t\(", usadas_texto):
            nivel, i, comillas, arg = 0, m.end(), None, ""
            while i < len(usadas_texto):
                ch = usadas_texto[i]
                if comillas:
                    arg += ch
                    if ch == "\\":
                        i += 1; arg += usadas_texto[i:i + 1]
                    elif ch == comillas:
                        comillas = None
                elif ch in "'\"`":
                    comillas = ch; arg += ch
                elif ch in "([{":
                    nivel += 1; arg += ch
                elif ch in ")]}":
                    if nivel == 0: break
                    nivel -= 1; arg += ch
                elif ch == "," and nivel == 0:
                    break
                else:
                    arg += ch
                i += 1
            llamadas += [x[1] for x in re.findall(r"""(['"`])((?:(?!\1)[^\\]|\\.)*)\1""", arg) if "." in x[1]]
        for archivo in sorted(os.listdir(loc_dir)):
            if not archivo.endswith(".json"):
                continue
            try:
                datos = json.loads(leer(os.path.join(loc_dir, archivo)))
            except ValueError:
                continue
            claves = []
            def aplanar(o, p=""):
                for k, v in o.items():
                    (aplanar(v, p + k + ".") if isinstance(v, dict) else claves.append(p + k))
            aplanar(datos)
            usadas = set()
            for ll in llamadas:
                if "${" in ll:
                    rx = re.compile("^" + re.sub(r"\\\$\\\{[^}]*\\\}", "[^.]+", re.escape(ll)) + "$")  # ${…} -> cualquier segmento
                    usadas |= {k for k in claves if rx.match(k)}
                elif ll.endswith("."):
                    usadas |= {k for k in claves if k.startswith(ll)}
                else:
                    usadas.add(ll)
            sin = [k for k in claves if k not in usadas]
            if sin:
                claves_sin_uso.append((archivo, sin))
            break  # con un idioma basta: los demás deben tener las mismas claves

    # dependencias de package.json que ningún archivo importa
    deps_sin_uso = []
    try:
        pkg = json.loads(leer(os.path.join(fe, "package.json")))
        for dep in sorted(pkg.get("dependencies", {})):
            if dep not in paquetes and dep not in vite and dep not in index:
                deps_sin_uso.append(dep)
    except ValueError:
        pass
    return {"sin_uso": sin_uso, "publicos": publicos, "claves": claves_sin_uso, "deps": deps_sin_uso, "alcanzados": len(alcanzados), "total": len(en_src)}


# =============================================================================== python
def raices_python(raiz):
    """Carpetas de primer nivel que contienen código Python (cada una se trata como su propia raíz de imports)."""
    out = []
    for nombre in sorted(os.listdir(raiz)):
        d = os.path.join(raiz, nombre)
        if os.path.isdir(d) and nombre not in IGNORAR and any(f.endswith(".py") for _, _, fs in caminar(d) for f in fs):
            out.append(d)
    return out


def modulo_a_archivo(modulo, base):
    p = os.path.join(base, *modulo.split("."))
    for cand in (p + ".py", os.path.join(p, "__init__.py")):
        if os.path.isfile(cand):
            return cand
    return None


def analizar_python(raiz, profundo=False):
    raices = raices_python(raiz)
    if not raices:
        return None
    infra = "\n".join(leer(p) for p in todos_los_archivos(raiz)
                      if os.path.basename(p) in ("Makefile", "podman-compose.yml", "docker-compose.yml", "compose.yml", "compose.yaml")
                      or os.path.basename(p).startswith(("Containerfile", "Dockerfile")) or p.endswith((".sh", ".yml", ".yaml", ".toml", ".cfg")))
    resultado = {"sin_uso": [], "imports": [], "funciones": [], "total": 0}
    for base in raices:
        archivos = [f for f in todos_los_archivos(base) if f.endswith(".py")]
        resultado["total"] += len(archivos)
        arboles = {}
        for f in archivos:
            try:
                arboles[f] = ast.parse(leer(f), f)
            except SyntaxError:
                continue
        entradas = set()
        for f, arbol in arboles.items():
            nombre = os.path.basename(f)
            modulo = os.path.splitext(os.path.relpath(f, base))[0].replace(os.sep, ".")
            es_main = any(isinstance(n, ast.If) and "__main__" in ast.dump(n.test) for n in arbol.body)
            es_test = nombre.startswith("test_") or nombre.endswith("_test.py") or nombre == "conftest.py" or "tests" in os.path.relpath(f, base).split(os.sep)
            en_infra = re.search(r"(?<![\w.])" + re.escape(os.path.splitext(nombre)[0]) + r"(\.py|:\w+)", infra) or re.search(re.escape(modulo.replace(".", "/")) + r"\.py", infra) or re.search(r"(?<![\w.])" + re.escape(modulo) + r":\w+", infra)
            if es_main or es_test or en_infra or nombre in ("__init__.py", "__main__.py", "manage.py", "wsgi.py", "asgi.py", "setup.py"):
                entradas.add(f)
        alcanzados, pendientes = set(), list(entradas)
        while pendientes:
            f = pendientes.pop()
            if f in alcanzados or f not in arboles:
                continue
            alcanzados.add(f)
            paquete = os.path.relpath(os.path.dirname(f), base).replace(os.sep, ".")
            for n in ast.walk(arboles[f]):
                objetivos = []
                if isinstance(n, ast.Import):
                    objetivos = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    if n.level:
                        partes = paquete.split(".") if paquete != "." else []
                        partes = partes[: len(partes) - (n.level - 1)] if n.level > 1 else partes
                        pref = ".".join(partes)
                        mod = (pref + "." + n.module) if n.module and pref else (n.module or pref)
                    else:
                        mod = n.module
                    if mod:
                        objetivos = [mod] + [mod + "." + a.name for a in n.names]
                    else:
                        objetivos = [a.name for a in n.names]
                for o in objetivos:
                    destino = modulo_a_archivo(o, base)
                    if destino:
                        pendientes.append(destino)
                        # un paquete importado trae consigo su __init__
        sin = sorted(f for f in archivos if f not in alcanzados and f in arboles)
        resultado["sin_uso"] += sin
        # imports sin usar
        for f, arbol in arboles.items():
            if os.path.basename(f) == "__init__.py":
                continue
            lineas = leer(f).splitlines()
            usados = {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)} | {n.value.id for n in ast.walk(arbol) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
            for n in arbol.body:
                if isinstance(n, (ast.Import, ast.ImportFrom)) and "noqa" not in lineas[n.lineno - 1]:
                    for a in n.names:
                        local = (a.asname or a.name).split(".")[0]
                        if local != "*" and local not in usados:
                            resultado["imports"].append(f"{rel(f, raiz)}:{n.lineno}  «{a.name}»")
        if profundo:
            todo = "\n".join(leer(f) for f in archivos)
            for f, arbol in arboles.items():
                for n in arbol.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.decorator_list:
                        nombre = n.name
                        if nombre.startswith(("test", "_")) or nombre in ("main",) or "tests" in f.split(os.sep):
                            continue
                        if len(re.findall(r"\b" + re.escape(nombre) + r"\b", todo)) <= 1:  # solo su definición; los usos como modulo.nombre() también cuentan
                            resultado["funciones"].append(f"{rel(f, raiz)}:{n.lineno}  {nombre}")
    return resultado


# =============================================================================== comunes
def basura_y_huerfanos(raiz):
    basura = [p for p in todos_los_archivos(raiz) if BASURA.search(os.path.basename(p))]
    referencias = "\n".join(leer(p) for p in todos_los_archivos(raiz) if os.path.basename(p) in ("Makefile",) or p.endswith((".md", ".yml", ".yaml")))
    huerfanos = []
    for f in os.listdir(raiz):
        ruta = os.path.join(raiz, f)
        if os.path.isfile(ruta) and f.endswith((".sh", ".py")) and f not in referencias:
            huerfanos.append(ruta)
    return basura, huerfanos


BASURA_SISTEMA = (".DS_Store", "Thumbs.db", "desktop.ini")
MARCADORES = (".gitkeep", ".keep")


def carpetas_vacias(raiz):
    """(vacías, con_marcador).

    Vacía = no contiene nada salvo carpetas vacías o basura del sistema (.DS_Store…).
    Una carpeta con .gitkeep NO es vacía: el marcador está ahí a propósito. Y como ese marcador es contenido,
    también protege a todas las carpetas que la contienen (si no, se borraría el padre y el marcador con él).
    """
    vacias, marcadores = [], []
    for dirpath, dirs, archivos in os.walk(raiz, topdown=False):
        if dirpath == raiz or any(p in IGNORAR for p in os.path.relpath(dirpath, raiz).split(os.sep)):
            continue
        hay_marcador = hay_otro = False
        for d, ds, fs in os.walk(dirpath):
            ds[:] = [x for x in ds if x not in IGNORAR]
            for f in fs:
                if f in MARCADORES:
                    hay_marcador = True
                elif f not in BASURA_SISTEMA:
                    hay_otro = True
        if hay_otro:
            continue
        if hay_marcador:
            if any(a in MARCADORES for a in archivos):
                marcadores.append(dirpath)   # la carpeta que tiene el marcador, no sus padres
        else:
            vacias.append(dirpath)
    return sorted(vacias, key=lambda p: -p.count(os.sep)), sorted(marcadores)


def quitar_vacias(vacias):
    """Borra carpetas vacías de la más profunda a la más superficial. NUNCA usa rmtree: si aparece algo
    inesperado dentro, rmdir falla y la carpeta se queda."""
    n = 0
    for d in vacias:
        try:
            for f in os.listdir(d):
                if f in BASURA_SISTEMA and os.path.isfile(os.path.join(d, f)):
                    os.remove(os.path.join(d, f))
            os.rmdir(d)
            n += 1
        except OSError:
            pass
    return n


def cachés(raiz):
    encontrados = []
    for dirpath, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "env"}]
        for d in list(dirs):
            if d in CACHES:
                encontrados.append(os.path.join(dirpath, d)); dirs.remove(d)
        for a in archivos:
            if a == ".coverage" or a.endswith(".pyc"):
                encontrados.append(os.path.join(dirpath, a))
    for extra in ("frontend/dist",):
        p = os.path.join(raiz, extra)
        if os.path.isdir(p):
            encontrados.append(p)
    return sorted(set(encontrados))


def peso(ruta):
    if os.path.isfile(ruta):
        return os.path.getsize(ruta)
    return sum(os.path.getsize(os.path.join(d, a)) for d, _, fs in os.walk(ruta) for a in fs if os.path.exists(os.path.join(d, a)))


def esta_en_git(ruta, raiz):
    try:
        return subprocess.run(["git", "-C", raiz, "ls-files", "--error-unmatch", ruta], capture_output=True).returncode == 0
    except OSError:
        return False


def guardar_respaldo(rutas, raiz, destino):
    """Guarda copia de los archivos en un .tgz ANTES de borrarlos (rutas relativas a la raíz del repo)."""
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    with tarfile.open(destino, "w:gz") as tar:
        for r in rutas:
            if os.path.isfile(r):
                tar.add(r, arcname=os.path.relpath(r, raiz))
    os.chmod(destino, 0o600)
    print(f"  respaldo de lo que se va a borrar: {destino}")
    print(f"  (para recuperarlo:  tar xzf {destino} -C {raiz})")


def borrar(rutas, raiz, auto, modo="archivos", respaldo=None):
    if not rutas:
        return 0
    if not auto:
        try:
            r = input(f"\n¿Borrar estos {len(rutas)} elementos? [s/N] ").strip().lower()
        except EOFError:
            r = ""
        if r not in ("s", "si", "sí", "y", "yes"):
            print("Cancelado: no se borró nada.")
            return 0
    if respaldo and modo == "archivos":
        guardar_respaldo(rutas, raiz, respaldo)
    n = 0
    for ruta in rutas:
        real = os.path.realpath(ruta)
        if not real.startswith(os.path.realpath(raiz) + os.sep):
            print(ambar(f"  se omite (fuera del repositorio): {ruta}"))
            continue
        if os.path.isdir(ruta) and not os.path.islink(ruta):
            if modo == "cache":
                shutil.rmtree(ruta, ignore_errors=True)   # los cachés se regeneran solos
            else:
                n += quitar_vacias([ruta]); continue
        elif esta_en_git(ruta, raiz):
            subprocess.run(["git", "-C", raiz, "rm", "-q", "-f", "--", ruta], capture_output=True)
        else:
            try:
                os.remove(ruta)
            except OSError:
                continue
        n += 1
    # lo que haya quedado vacío tras borrar archivos
    n += quitar_vacias(carpetas_vacias(raiz)[0]) if modo != "vacias" else 0
    print(verde(f"✓ {n} elementos borrados"))
    return n


def cmd_sin_uso(raiz, args):
    seguros = []
    print(negrita("\nArchivos sin uso"))
    fe = analizar_frontend(raiz)
    if fe:
        print(f"\n  Frontend: {fe['alcanzados']} de {fe['total']} archivos de src/ se alcanzan desde index.html")
        for f in fe["sin_uso"]:
            print(f"   {ambar('SEGURO')}  {rel(f, raiz)}   (nada lo importa)")
        for f in fe["publicos"]:
            print(f"   {ambar('SEGURO')}  {rel(f, raiz)}   (ningún archivo ni documento lo menciona)")
        seguros += fe["sin_uso"] + fe["publicos"]
        if not fe["sin_uso"] and not fe["publicos"]:
            print(verde("   ✓ no hay archivos sin uso en el frontend"))
        for archivo, claves in fe["claves"]:
            print(f"   REVISAR  {len(claves)} claves de traducción sin uso en {archivo}: " + ", ".join(claves[:8]) + (" …" if len(claves) > 8 else ""))
        for d in fe["deps"]:
            print(f"   REVISAR  dependencia «{d}» en package.json: ningún archivo la importa")
    py = analizar_python(raiz, profundo=args.profundo)
    if py:
        print(f"\n  Python: {py['total']} archivos .py")
        for f in py["sin_uso"]:
            print(f"   {ambar('SEGURO')}  {rel(f, raiz)}   (ningún módulo lo importa y nada lo ejecuta)")
        seguros += py["sin_uso"]
        if not py["sin_uso"]:
            print(verde("   ✓ no hay módulos sin uso"))
        for i in py["imports"][:25]:
            print(f"   REVISAR  import sin usar  {i}")
        if len(py["imports"]) > 25:
            print(f"   REVISAR  … y {len(py['imports']) - 25} imports sin usar más")
        for fn in py["funciones"]:
            print(f"   REVISAR  nunca se menciona  {fn}")
    basura, huerfanos = basura_y_huerfanos(raiz)
    if basura or huerfanos:
        print("\n  Archivos sueltos")
    for f in basura:
        print(f"   {ambar('SEGURO')}  {rel(f, raiz)}   (basura: copia de respaldo, log o archivo del sistema)")
    for f in huerfanos:
        print(f"   REVISAR  {rel(f, raiz)}   (script de la raíz que ni el Makefile ni los documentos mencionan)")
    seguros += basura
    seguros = sorted(set(seguros))
    print(f"\n  Resumen: {len(seguros)} elementos SEGUROS de borrar" + ("" if seguros else " — todo en orden"))
    if args.borrar:
        borrar(seguros, raiz, args.yes, respaldo=args.respaldo)
    elif seguros:
        print("  (para borrarlos: python tools/mantenimiento.py sin-uso --borrar)")
    return seguros


def cmd_vacias(raiz, args):
    print(negrita("\nCarpetas vacías"))
    vacias, marcadores = carpetas_vacias(raiz)
    for d in vacias:
        print(f"   {ambar('VACÍA')}  {rel(d, raiz)}/")
    for d in marcadores:
        print(f"   se conserva  {rel(d, raiz)}/   (tiene .gitkeep a propósito)")
    if not vacias:
        print(verde("   ✓ no hay carpetas vacías"))
    if args.borrar:
        borrar(vacias, raiz, args.yes, modo="vacias")
    elif vacias:
        print("  (para borrarlas: python tools/mantenimiento.py vacias --borrar)")
    return vacias


def cmd_cache(raiz, args):
    print(negrita("\nCachés y artefactos regenerables"))
    cs = cachés(raiz)
    total = 0
    for p in cs:
        t = peso(p); total += t
        print(f"   {ambar('CACHÉ')}  {rel(p, raiz)}   ({tamano(t)})")
    if not cs:
        print(verde("   ✓ no hay cachés"))
    else:
        print(f"  Total: {tamano(total)} (se regeneran solos)")
    if args.borrar:
        borrar(cs, raiz, args.yes, modo="cache")
    return cs


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mantenimiento del repositorio", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("comando", choices=["sin-uso", "vacias", "cache", "todo"])
    ap.add_argument("--raiz", default=None, help="raíz del repositorio (por defecto, la carpeta que contiene tools/)")
    ap.add_argument("--borrar", action="store_true", help="ofrecer borrar lo que es SEGURO borrar")
    ap.add_argument("-y", "--yes", action="store_true", help="no preguntar antes de borrar")
    ap.add_argument("--respaldo", default=None, help="antes de borrar archivos, guárdalos en este .tgz")
    ap.add_argument("--profundo", action="store_true", help="además, funciones y clases de Python que nunca se mencionan")
    ap.add_argument("--check", action="store_true", help="termina con código 1 si hay algo SEGURO de borrar (para CI)")
    args = ap.parse_args(argv)
    raiz = os.path.abspath(args.raiz or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    if not os.path.isdir(raiz):
        print(f"No existe la raíz: {raiz}")
        return 2
    if args.comando == "todo":
        args.borrar = False
    hallazgos = []
    if args.comando in ("sin-uso", "todo"):
        hallazgos += cmd_sin_uso(raiz, args)
    if args.comando in ("vacias", "todo"):
        hallazgos += cmd_vacias(raiz, args)
    if args.comando in ("cache", "todo"):
        cmd_cache(raiz, args)
    print()
    return 1 if (args.check and hallazgos) else 0


if __name__ == "__main__":
    sys.exit(main())

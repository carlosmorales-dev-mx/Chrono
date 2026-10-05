#!/usr/bin/env python3
"""Revisión ESTÁTICA de la configuración de contenedores y CI (no construye ni ejecuta nada).

    python tools/verificar_contenedores.py [RAIZ]       (necesita PyYAML: pip install pyyaml)

Atrapa los errores típicos antes de gastar minutos construyendo imágenes:
  · Containerfiles: nombres de imagen completos y con etiqueta fija, COPY a archivos que existen, ningún .env
    dentro de la imagen, usuario sin privilegios, comandos en formato exec válido, apt/pip sin basura.
  · compose: contextos y env_file que existen, depends_on válidos, puertos solo en 127.0.0.1, sin secretos
    escritos a mano, healthchecks, volúmenes declarados.
  · nginx: llaves balanceadas, el proxy apunta a un servicio y a un puerto REALES, /internal/ bloqueado.
  · GitHub Actions y Dependabot: estructura, versiones fijas de las acciones, archivos que se invocan existen.
Termina con código 1 si hay algún error.
"""
import glob
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("Falta PyYAML:  pip install pyyaml")
    sys.exit(2)

RAIZ = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
errores, avisos, comprobaciones = [], [], 0


def ruta(*p):
    return os.path.join(RAIZ, *p)


def rel(p):
    return os.path.relpath(p, RAIZ).replace(os.sep, "/")


def err(m):
    errores.append(m)
    print("  ✗", m)


def warn(m):
    avisos.append(m)
    print("  !", m)


def ok(m):
    global comprobaciones
    comprobaciones += 1
    print("  ✓", m)


def leer(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# ============================================================================== Containerfiles
def instrucciones(texto):
    """[(número_de_línea, INSTRUCCIÓN, argumentos)] uniendo las líneas que terminan en \\ ."""
    salida, acumulado, inicio = [], "", 0
    for n, linea in enumerate(texto.splitlines(), 1):
        s = linea.rstrip()
        if not acumulado:
            if not s.strip() or s.strip().startswith("#"):
                continue
            inicio = n
        if s.endswith("\\"):
            acumulado += s[:-1] + " "
            continue
        acumulado += s
        partes = acumulado.strip().split(None, 1)
        salida.append((inicio, partes[0].upper(), partes[1] if len(partes) > 1 else ""))
        acumulado = ""
    return salida


def sustituir(texto, variables):
    return re.sub(r"\$\{(\w+)(?::?-([^}]*))?\}|\$(\w+)", lambda m: variables.get(m.group(1) or m.group(3), m.group(2) if m.group(2) is not None else m.group(0)), texto)


def revisar_containerfile(archivo, exigir_no_root):
    nombre = rel(archivo)
    contexto = os.path.dirname(archivo)
    e0 = len(errores)
    ins = instrucciones(leer(archivo))
    args, etapas, hay_from, usuario_final, expuestos = {}, [], False, None, []
    for n, i, a in ins:
        if i == "ARG" and not hay_from:
            k, _, v = a.partition("=")
            args[k.strip()] = v.strip().strip('"')
        elif i == "FROM":
            hay_from, usuario_final = True, None
            m = re.match(r"(?:--platform=\S+\s+)?(\S+)(?:\s+[Aa][Ss]\s+(\S+))?", a)
            imagen = sustituir(m.group(1), args)
            if "$" in imagen:
                err(f"{nombre}:{n}: la imagen «{m.group(1)}» usa una variable que no tiene valor por defecto (ARG antes del primer FROM)")
            partes_imagen = imagen.split("/")
            primer = partes_imagen[0]
            # Solo hay registro si hay más de un componente y el primero parece un servidor (docker.io, ghcr.io, localhost:5000…).
            tiene_registro = len(partes_imagen) > 1 and ("." in primer or ":" in primer or primer == "localhost")
            if imagen not in etapas and not tiene_registro:
                err(f"{nombre}:{n}: «{imagen}» es un nombre corto; Podman pide el nombre completo (p. ej. docker.io/library/{imagen})")
            etiqueta = imagen.rsplit(":", 1)[1] if ":" in imagen.split("/")[-1] else None
            if imagen not in etapas:
                if etiqueta is None:
                    err(f"{nombre}:{n}: «{imagen}» no fija una versión (se usaría :latest)")
                elif etiqueta == "latest":
                    err(f"{nombre}:{n}: «{imagen}» usa :latest; fija una versión")
            if m.group(2):
                etapas.append(m.group(2))
        elif i in ("COPY", "ADD"):
            partes = a.split()
            banderas = [p for p in partes if p.startswith("--")]
            rutas = [p for p in partes if not p.startswith("--")]
            origen = next((b.split("=", 1)[1] for b in banderas if b.startswith("--from=")), None)
            if origen:
                if origen not in etapas:
                    err(f"{nombre}:{n}: COPY --from={origen}: esa etapa no existe antes (etapas: {', '.join(etapas) or 'ninguna'})")
                continue
            for src in rutas[:-1]:
                if re.match(r"(^|/)\.env($|\.)", src) and not src.endswith(".example"):
                    err(f"{nombre}:{n}: copia «{src}» a la imagen: los .env tienen secretos y no deben ir dentro")
                elif src != "." and not glob.glob(os.path.join(contexto, src)):
                    err(f"{nombre}:{n}: COPY de «{src}», que no existe en {rel(contexto)}/")
        elif i == "USER":
            usuario_final = a.strip()
        elif i == "EXPOSE":
            expuestos += [int(p.split("/")[0]) for p in a.split() if p.split("/")[0].isdigit()]
        elif i in ("CMD", "ENTRYPOINT") and a.strip().startswith("["):
            try:
                v = json.loads(a)
                assert isinstance(v, list) and all(isinstance(x, str) for x in v)
            except (ValueError, AssertionError):
                err(f"{nombre}:{n}: {i} en formato exec no es un arreglo JSON de textos válido (usa comillas dobles)")
        elif i == "RUN":
            if "pip install" in a and "--no-cache-dir" not in a:
                err(f"{nombre}:{n}: pip install sin --no-cache-dir (engorda la imagen)")
            if "apt-get install" in a:
                if "--no-install-recommends" not in a:
                    err(f"{nombre}:{n}: apt-get install sin --no-install-recommends")
                if "/var/lib/apt/lists" not in a:
                    err(f"{nombre}:{n}: apt-get install sin limpiar /var/lib/apt/lists en el mismo RUN")
            if re.search(r"\bapt-get\s+install\b", a) and "apt-get update" not in a:
                err(f"{nombre}:{n}: apt-get install sin «apt-get update» en el mismo RUN")
    if not hay_from:
        err(f"{nombre}: no tiene FROM")
    if exigir_no_root and (usuario_final in (None, "root", "0")):
        err(f"{nombre}: la etapa final corre como root; agrega un USER sin privilegios")
    ignore = os.path.join(contexto, ".dockerignore")
    if not os.path.isfile(ignore):
        err(f"{rel(contexto)}/: falta .dockerignore (sin él, .env y node_modules/venv entran al contexto de construcción)")
    elif not re.search(r"^\.env\s*$", leer(ignore), flags=re.M):
        err(f"{rel(ignore)}: no excluye .env")
    if len(errores) == e0:
        ok(f"{nombre}: imágenes completas y con versión, COPY válidos, sin .env, {'usuario sin privilegios, ' if exigir_no_root else ''}comandos exec válidos")
    return expuestos


# ============================================================================== compose
def revisar_compose(archivo, puertos_expuestos):
    # El compose del STACK (todo en contenedores) es estricto; el de desarrollo (solo PostgreSQL para `make dev`)
    # necesita publicar el puerto de la base y usa una contraseña local de desarrollo.
    estricto = ".stack." in os.path.basename(archivo)
    nombre = rel(archivo)
    e0 = len(errores)
    try:
        d = yaml.safe_load(leer(archivo))
    except yaml.YAMLError as e:
        err(f"{nombre}: YAML inválido: {e}")
        return set()
    servicios = d.get("services") or {}
    if "version" in d:
        err(f"{nombre}: «version:» está obsoleto; quítalo")
    volumenes = set((d.get("volumes") or {}).keys())
    for sn, s in servicios.items():
        if not (s.get("image") or s.get("build")):
            err(f"{nombre}: el servicio «{sn}» no tiene image ni build")
        b = s.get("build")
        if b:
            ctx = b.get("context") if isinstance(b, dict) else b
            df = (b.get("dockerfile") if isinstance(b, dict) else None) or "Containerfile"
            if not os.path.isdir(ruta(os.path.dirname(archivo), ctx)) and not os.path.isdir(os.path.join(os.path.dirname(archivo), ctx)):
                err(f"{nombre}: build.context «{ctx}» de «{sn}» no existe")
            elif not os.path.isfile(os.path.join(os.path.dirname(archivo), ctx, df)):
                err(f"{nombre}: «{df}» no existe en {ctx}/ (servicio «{sn}»)")
        for ef in ([s["env_file"]] if isinstance(s.get("env_file"), str) else s.get("env_file") or []):
            destino = os.path.join(os.path.dirname(archivo), ef)
            if not os.path.isfile(destino):
                # Los .env están en .gitignore: en un clon limpio (y en el CI) solo existe el .env.example.
                if os.path.isfile(destino + ".example"):
                    warn(f"{nombre}: «{ef}» (de «{sn}») no existe todavía; se crea con:  cp {ef}.example {ef}") if not os.environ.get("CI") else None
                else:
                    err(f"{nombre}: env_file «{ef}» de «{sn}» no existe, ni siquiera su {ef}.example")
        dep = s.get("depends_on") or []
        for destino in (dep.keys() if isinstance(dep, dict) else dep):
            if destino not in servicios:
                err(f"{nombre}: «{sn}» depende de «{destino}», que no está definido")
        if isinstance(dep, dict):
            for destino, cfg in dep.items():
                cond = (cfg or {}).get("condition")
                if cond not in (None, "service_started", "service_healthy", "service_completed_successfully"):
                    err(f"{nombre}: condición de depends_on desconocida: {cond}")
                if cond == "service_healthy" and not servicios.get(destino, {}).get("healthcheck"):
                    err(f"{nombre}: «{sn}» espera que «{destino}» esté sano, pero «{destino}» no tiene healthcheck")
        for p in s.get("ports") or []:
            if not str(p).startswith("127.0.0.1:"):
                err(f"{nombre}: «{sn}» publica el puerto «{p}» a toda la red; usa 127.0.0.1:…")
        if estricto and sn in ("db", "backend", "worker") and s.get("ports"):
            err(f"{nombre}: «{sn}» no debería publicar puertos (solo el frontend los necesita)")
        for k, v in (s.get("environment") or {}).items():
            if re.search(r"PASS|SECRET|TOKEN|KEY", k, flags=re.I) and v not in (None, "") and not str(v).startswith("${"):
                (err if estricto else warn)(f"{nombre}: «{sn}» tiene {k} escrito a mano; usa ${{VARIABLE:-valor}} o env_file" + ("" if estricto else " (aceptable solo en desarrollo local)"))
        for v in s.get("volumes") or []:
            origen = str(v).split(":")[0]
            if not origen.startswith((".", "/", "~")) and origen not in volumenes:
                err(f"{nombre}: el volumen «{origen}» de «{sn}» no está declarado en volumes:")
        if "restart" not in s:
            warn(f"{nombre}: «{sn}» no tiene política de restart")
    for sn in (("db", "backend") if estricto else ("db",)):
        if sn in servicios and not servicios[sn].get("healthcheck"):
            err(f"{nombre}: «{sn}» necesita un healthcheck")
    if len(errores) == e0:
        ok(f"{nombre}: {len(servicios)} servicios; contextos, env_file y depends_on válidos; puertos solo en 127.0.0.1" + ("; sin secretos a mano" if estricto else ""))
    return set(servicios)


# ============================================================================== nginx
def revisar_nginx(archivo, servicios, puertos_por_servicio):
    nombre = rel(archivo)
    e0 = len(errores)
    texto = re.sub(r"#.*", "", leer(archivo))
    if texto.count("{") != texto.count("}"):
        err(f"{nombre}: las llaves no están balanceadas ({texto.count('{')} «{{» y {texto.count('}')} «}}»)")
    for n, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if s and not s.endswith((";", "{", "}")):
            err(f"{nombre}:{n}: la directiva «{s[:50]}» no termina en «;»")
    for m in re.finditer(r"proxy_pass\s+http://([\w.-]+)(?::(\d+))?([^;\s]*)\s*;", texto):
        host, puerto, uri = m.group(1), m.group(2), m.group(3)
        if servicios and host not in servicios:
            err(f"{nombre}: proxy_pass apunta a «{host}», que no es un servicio del compose ({', '.join(sorted(servicios))})")
        elif puerto and puertos_por_servicio.get(host) and int(puerto) not in puertos_por_servicio[host]:
            err(f"{nombre}: proxy_pass usa {host}:{puerto}, pero su Containerfile expone {sorted(puertos_por_servicio[host])}")
        if uri not in ("", "/"):
            warn(f"{nombre}: proxy_pass con ruta «{uri}»; en locations con regex no se permite una ruta en proxy_pass")
    if not re.search(r"location\s+/internal/\s*\{[^}]*(return\s+40[34]|deny\s+all)", texto):
        err(f"{nombre}: falta bloquear /internal/ (el ingest del worker no debe ser alcanzable desde fuera)")
    if "Upgrade" not in texto or "proxy_http_version 1.1" not in texto:
        err(f"{nombre}: el proxy del WebSocket necesita proxy_http_version 1.1 y la cabecera Upgrade")
    if not re.search(r"try_files\s+\$uri\s+\$uri/\s+/index\.html", texto):
        err(f"{nombre}: falta el respaldo a /index.html de la aplicación de una sola página")
    if len(errores) == e0:
        ok(f"{nombre}: llaves y directivas bien formadas, el proxy apunta a un servicio y puerto reales, /internal/ bloqueado, WebSocket y SPA configurados")


# ============================================================================== GitHub Actions / Dependabot
def revisar_workflow(archivo):
    nombre = rel(archivo)
    e0 = len(errores)
    try:
        d = yaml.safe_load(leer(archivo))
    except yaml.YAMLError as e:
        return err(f"{nombre}: YAML inválido: {e}")
    disparadores = d.get(True, d.get("on"))  # PyYAML interpreta «on» como True
    if not disparadores:
        err(f"{nombre}: no define cuándo se ejecuta (on:)")
    if "permissions" not in d:
        err(f"{nombre}: falta permissions: al nivel superior (por defecto el token tendría más permisos de los necesarios)")
    jobs = d.get("jobs") or {}
    for jn, j in jobs.items():
        if "runs-on" not in j:
            err(f"{nombre}: el job «{jn}» no tiene runs-on")
        if not j.get("steps"):
            err(f"{nombre}: el job «{jn}» no tiene pasos")
        if "timeout-minutes" not in j:
            warn(f"{nombre}: el job «{jn}» no tiene timeout-minutes")
        for destino in ([j["needs"]] if isinstance(j.get("needs"), str) else j.get("needs") or []):
            if destino not in jobs:
                err(f"{nombre}: el job «{jn}» necesita «{destino}», que no existe")
        for paso in j.get("steps") or []:
            if "uses" in paso:
                if "@" not in paso["uses"]:
                    err(f"{nombre}: «{paso['uses']}» no fija versión (usa @v4, un SHA…)")
            elif "run" not in paso:
                err(f"{nombre}: un paso del job «{jn}» no tiene ni uses ni run")
            base = paso.get("working-directory") or (j.get("defaults") or {}).get("run", {}).get("working-directory") or "."
            for subir, ref in re.findall(r"(?<![\w/-])((?:\.\./)*)((?:tools|backend|worker|frontend)/[\w./-]+\.(?:py|sh|json|ya?ml|txt))", str(paso.get("run", ""))):
                candidato = os.path.normpath(os.path.join(ruta(base), subir + ref)) if subir else ruta(ref)
                if not os.path.exists(candidato):
                    err(f"{nombre}: el paso invoca «{subir}{ref}», que no existe en el repo")
            if re.search(r"secrets\.", str(paso)):
                warn(f"{nombre}: usa secretos; confirma que de verdad hacen falta")
    if len(errores) == e0:
        ok(f"{nombre}: estructura válida, {len(jobs)} jobs, acciones con versión fija, permisos mínimos, archivos invocados existen")


def revisar_dependabot(archivo):
    nombre = rel(archivo)
    e0 = len(errores)
    d = yaml.safe_load(leer(archivo)) or {}
    if d.get("version") != 2:
        err(f"{nombre}: version debe ser 2")
    for u in d.get("updates") or []:
        directorio = u.get("directory", "/")
        if not os.path.isdir(ruta(directorio.lstrip("/"))):
            err(f"{nombre}: el directorio «{directorio}» de {u.get('package-ecosystem')} no existe")
        if u.get("package-ecosystem") == "pip" and not os.path.isfile(ruta(directorio.lstrip("/"), "requirements.txt")):
            err(f"{nombre}: no hay requirements.txt en {directorio}")
        if u.get("package-ecosystem") == "npm" and not os.path.isfile(ruta(directorio.lstrip("/"), "package.json")):
            err(f"{nombre}: no hay package.json en {directorio}")
    if len(errores) == e0:
        ok(f"{nombre}: ecosistemas y carpetas válidos")


# ============================================================================== principal
def main():
    print(f"\nRevisando {RAIZ}\n")
    print("[1] Containerfiles")
    puertos_por_servicio = {}
    encontrados = sorted(glob.glob(ruta("*", "Containerfile*")))
    if not encontrados:
        print("  (no hay Containerfiles)")
    for cf in encontrados:
        carpeta = os.path.basename(os.path.dirname(cf))
        puertos_por_servicio[carpeta] = revisar_containerfile(cf, exigir_no_root=carpeta in ("backend", "worker"))

    print("\n[2] compose")
    servicios = set()
    for cp in sorted(glob.glob(ruta("podman-compose*.yml")) + glob.glob(ruta("docker-compose*.yml")) + glob.glob(ruta("compose*.y*ml"))):
        servicios |= revisar_compose(cp, puertos_por_servicio)

    print("\n[3] nginx")
    for ng in sorted(glob.glob(ruta("*", "nginx*.conf"))):
        revisar_nginx(ng, servicios, puertos_por_servicio)

    print("\n[4] GitHub Actions y Dependabot")
    flujos = sorted(glob.glob(ruta(".github", "workflows", "*.y*ml")))
    if not flujos:
        print("  (no hay workflows)")
    for w in flujos:
        revisar_workflow(w)
    for db in glob.glob(ruta(".github", "dependabot.y*ml")):
        revisar_dependabot(db)

    print(f"\nRESULTADO: {len(errores)} errores, {len(avisos)} avisos, {comprobaciones} grupos de comprobaciones correctos")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

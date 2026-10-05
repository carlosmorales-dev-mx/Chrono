"""Lógica de decisión de Chrono, en Python PURO (sin FastAPI, SQLAlchemy ni red).

Está separada a propósito: así se puede probar sin base de datos (backend/tests/) y las rutas
quedan como un pegamento fino. Todo lo que "decide algo" vive aquí:

  · validar nombres y URLs de servicios (incluye la defensa contra SSRF)
  · decidir cuándo abrir, escalar o cerrar un incidente (con histéresis)
  · resumir el historial de chequeos por tramos de tiempo, sin perder las caídas
  · calcular percentiles
  · dibujar la insignia SVG sin permitir inyección de código
"""
import ipaddress
import math
from collections import namedtuple
from datetime import timedelta
from html import escape
from urllib.parse import urlsplit

ESTADOS = ("up", "degraded", "down")
GRAVEDAD = {"up": 0, "degraded": 1, "down": 2}

NOMBRE_MAX = 80
URL_MAX = 2048


# --------------------------------------------------------------------------- servicios
def validar_nombre(valor: str) -> str:
    nombre = (valor or "").strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío")
    if len(nombre) > NOMBRE_MAX:
        raise ValueError(f"El nombre no puede pasar de {NOMBRE_MAX} caracteres")
    if any(ord(c) < 32 or ord(c) == 127 for c in nombre):
        raise ValueError("El nombre no puede contener saltos de línea ni caracteres de control")
    return nombre


def ip_prohibida(ip, permitir_privados: bool = False) -> bool:
    """¿Esta dirección IP es un destino al que el worker NO debe conectarse?

    Siempre se bloquea lo que nunca es un servicio público legítimo (enlace local, multicast,
    "no especificada": incluye el servicio de metadatos de la nube, 169.254.169.254).
    Lo interno (loopback, redes privadas, CGNAT…) se bloquea salvo que `permitir_privados` sea True.
    """
    if isinstance(ip, str):
        ip = ipaddress.ip_address(ip)
    if getattr(ip, "ipv4_mapped", None) is not None:  # ::ffff:127.0.0.1 es 127.0.0.1
        ip = ip.ipv4_mapped
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return True
    if not ip.is_global:  # loopback, privadas, CGNAT, reservadas…
        return not permitir_privados
    return False


def _nombre_interno(host: str) -> bool:
    host = host.lower().rstrip(".")
    return host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa", ".intranet"))


def validar_url(valor: str, permitir_privados: bool = False) -> str:
    """Valida la URL de un servicio y la devuelve limpia. Lanza ValueError con un mensaje claro."""
    url = (valor or "").strip()
    if not url:
        raise ValueError("La URL no puede estar vacía")
    if len(url) > URL_MAX:
        raise ValueError(f"La URL no puede pasar de {URL_MAX} caracteres")
    if any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("La URL no puede contener espacios ni caracteres de control")
    try:
        partes = urlsplit(url)
        puerto = partes.port  # lanza ValueError si el puerto es inválido
    except ValueError:
        raise ValueError("La URL no es válida")
    if partes.scheme not in ("http", "https"):
        raise ValueError("La URL debe empezar con http:// o https://")
    host = partes.hostname
    if not host:
        raise ValueError("La URL no tiene un dominio")
    if partes.username is not None or partes.password is not None:
        raise ValueError("La URL no puede incluir usuario ni contraseña")
    if puerto is not None and not (1 <= puerto <= 65535):
        raise ValueError("El puerto de la URL no es válido")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip_prohibida(ip, permitir_privados):
            raise ValueError("Esa dirección no está permitida (es interna o reservada)")
    elif _nombre_interno(host) and not permitir_privados:
        raise ValueError("Esa dirección no está permitida (apunta a la red interna)")
    return url


# --------------------------------------------------------------------------- incidentes
Accion = namedtuple("Accion", ["tipo", "severidad"])  # tipo: "abrir" | "cerrar" | "escalar" | None
NADA = Accion(None, None)


def _peor(estados) -> str:
    return max(estados, key=lambda e: GRAVEDAD.get(e, 0))


def decidir_incidente(ultimos, severidad_abierta, abrir_tras: int = 2, cerrar_tras: int = 3) -> Accion:
    """Decide qué hacer con el incidente de un servicio tras un chequeo nuevo.

    `ultimos`: estados recientes del servicio, el MÁS NUEVO PRIMERO e INCLUYENDO el chequeo actual.
    `severidad_abierta`: estado del incidente abierto ("degraded"/"down") o None si no hay ninguno.

    Histéresis: un solo chequeo malo no abre un incidente (hacen falta `abrir_tras` seguidos) y un solo
    chequeo bueno no lo cierra (hacen falta `cerrar_tras` seguidos). Así un servicio que oscila alrededor
    de un umbral no genera decenas de incidentes de 30 segundos.
    """
    abrir_tras = max(1, abrir_tras)
    cerrar_tras = max(1, cerrar_tras)
    if not ultimos:
        return NADA
    if severidad_abierta is None:
        ventana = list(ultimos[:abrir_tras])
        if len(ventana) == abrir_tras and all(e != "up" for e in ventana):
            return Accion("abrir", _peor(ventana))
        return NADA
    ventana = list(ultimos[:cerrar_tras])
    if len(ventana) == cerrar_tras and all(e == "up" for e in ventana):
        return Accion("cerrar", None)
    if ultimos[0] == "down" and severidad_abierta == "degraded":
        return Accion("escalar", "down")  # empeoró durante el mismo incidente: se refleja la peor severidad
    return NADA


# --------------------------------------------------------------------------- historial
def agrupar_historial(filas, ahora, horas: int = 24, puntos_max: int = 96, ancho_min_s: int = 60):
    """Resume los chequeos de las últimas `horas` en tramos de tiempo IGUALES, sin perder las caídas.

    `filas`: iterable de (creado_en, estado, latencia_ms) con fechas con zona horaria. `ahora`: datetime.

    El ancho del tramo se adapta a los datos disponibles (no a la ventana fija): un servicio recién agregado
    muestra enseguida sus puntos reales, y uno con 24 h de historia se resume a ~`puntos_max` tramos.
    Cada tramo devuelve el PEOR estado visto y la latencia media de los chequeos que sí respondieron
    (None si todos fallaron), así una caída de un minuto sigue siendo visible en el historial.
    """
    inicio_ventana = ahora - timedelta(hours=horas)
    datos = sorted((f for f in filas if f[0] > inicio_ventana and f[0] <= ahora), key=lambda f: f[0])
    if not datos:
        return []
    t0 = datos[0][0]
    span = max((ahora - t0).total_seconds(), 1.0)
    ancho = max(ancho_min_s, math.ceil(span / max(1, puntos_max)))

    tramos = {}
    for creado_en, estado, latencia in datos:
        idx = int((creado_en - t0).total_seconds() // ancho)
        t = tramos.setdefault(idx, {"ultimo": creado_en, "n": 0, "estados": [], "lats": []})
        t["ultimo"] = creado_en
        t["n"] += 1
        t["estados"].append(estado)
        if latencia is not None:
            t["lats"].append(latencia)

    salida = []
    for idx in sorted(tramos):
        t = tramos[idx]
        salida.append({
            "creado_en": t["ultimo"].isoformat(),
            "latencia_ms": round(sum(t["lats"]) / len(t["lats"])) if t["lats"] else None,
            "latencia_max": max(t["lats"]) if t["lats"] else None,
            "estado": _peor(t["estados"]),
            "n": t["n"],
        })
    return salida


def percentil(valores, p: float):
    """Percentil con interpolación lineal (igual que percentile_cont de PostgreSQL). None si no hay datos."""
    v = sorted(x for x in valores if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return round(v[0])
    pos = max(0.0, min(1.0, p)) * (len(v) - 1)
    bajo = int(math.floor(pos))
    alto = int(math.ceil(pos))
    return round(v[bajo] + (v[alto] - v[bajo]) * (pos - bajo))


# --------------------------------------------------------------------------- insignia SVG
_COLORES = {"up": "#1A6E5C", "degraded": "#6B4A18", "down": "#6B1E2E", None: "#4A3468"}
_TEXTOS = {"up": "operativo", "degraded": "degradado", "down": "caído", None: "sin datos"}
_ANCHO_CARACTER = 7
BADGE_NOMBRE_MAX = 32


def construir_badge(nombre: str, estado) -> str:
    """SVG de la insignia de un servicio. El nombre SIEMPRE se escapa: lo controla quien crea el servicio."""
    nombre = nombre or ""
    if len(nombre) > BADGE_NOMBRE_MAX:
        nombre = nombre[: BADGE_NOMBRE_MAX - 1] + "…"
    texto_estado = _TEXTOS.get(estado, _TEXTOS[None])
    color = _COLORES.get(estado, _COLORES[None])
    ancho_nombre = _ANCHO_CARACTER * len(nombre) + 20
    ancho_estado = _ANCHO_CARACTER * len(texto_estado) + 20
    total = ancho_nombre + ancho_estado
    seguro = escape(nombre, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="24" role="img" aria-label="{seguro}: {texto_estado}">\n'
        f'  <rect width="{ancho_nombre}" height="24" fill="#0D0714" rx="4"/>\n'
        f'  <rect x="{ancho_nombre}" width="{ancho_estado}" height="24" fill="{color}" rx="4"/>\n'
        f'  <rect x="{ancho_nombre - 4}" width="4" height="24" fill="{color}"/>\n'
        f'  <text x="{ancho_nombre / 2}" y="16" font-family="Verdana,sans-serif" font-size="11" fill="#F5EAD3" text-anchor="middle">{seguro}</text>\n'
        f'  <text x="{ancho_nombre + ancho_estado / 2}" y="16" font-family="Verdana,sans-serif" font-size="11" fill="#F5EAD3" text-anchor="middle">{texto_estado}</text>\n'
        f'</svg>'
    )

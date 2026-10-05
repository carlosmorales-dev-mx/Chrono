"""Lógica pura del worker (sin red ni httpx), separada para poder probarla sin conexión.

OJO: ip_prohibida y objetivo_permitido deben comportarse igual que en backend/dominio.py. Hay una prueba
de paridad (backend/tests/test_paridad.py) que lo vigila.
"""
import ipaddress
from urllib.parse import urlsplit


def clasificar(codigo_http: int, latencia_ms: int, umbral_ms: int) -> str:
    """Estado de un chequeo que SÍ obtuvo respuesta.

    5xx -> down (el servicio está fallando) · 4xx -> degraded · respuesta correcta pero más lenta que el umbral -> degraded.
    """
    if codigo_http >= 500:
        return "down"
    if codigo_http >= 400:
        return "degraded"
    if latencia_ms > umbral_ms:
        return "degraded"
    return "up"


def ip_prohibida(ip, permitir_privados: bool = False) -> bool:
    if isinstance(ip, str):
        ip = ipaddress.ip_address(ip)
    if getattr(ip, "ipv4_mapped", None) is not None:
        ip = ip.ipv4_mapped
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return True
    if not ip.is_global:
        return not permitir_privados
    return False


def objetivo_permitido(url: str, permitir_privados: bool, resolver) -> bool:
    """¿Puede el worker conectarse a esta URL? Defensa contra SSRF: aunque el backend ya valida las URLs al
    crearlas, un nombre público puede RESOLVER a una IP interna (o cambiarla después), así que se comprueba
    otra vez, con la IP real, justo antes de cada chequeo.

    `resolver(host, puerto)` devuelve una lista de IPs (str). Si el nombre no resuelve, se permite: la petición
    fallará sola y quedará registrada como caída, que es lo correcto.
    """
    try:
        partes = urlsplit(url)
        host = partes.hostname
        puerto = partes.port or (443 if partes.scheme == "https" else 80)
    except ValueError:
        return False
    if partes.scheme not in ("http", "https") or not host:
        return False
    try:
        return not ip_prohibida(ipaddress.ip_address(host), permitir_privados)
    except ValueError:
        pass  # no es una IP literal: es un nombre
    try:
        ips = resolver(host, puerto)
    except OSError:
        return True
    return not any(ip_prohibida(ip, permitir_privados) for ip in ips)

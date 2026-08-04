"""Carga los 8 servicios iniciales -- correr UNA sola vez despues de
init_db.py. Si ya existen (por nombre), no los duplica."""
from database import SessionLocal
import db_models

SERVICIOS_INICIALES = [
    ("OpenAI API", "https://status.openai.com"),
    ("Anthropic API", "https://status.anthropic.com"),
    ("DeepSeek API", "https://status.deepseek.com"),
    ("GitHub API", "https://api.github.com"),
    ("Cloudflare", "https://www.cloudflarestatus.com"),
    ("Vercel", "https://www.vercel-status.com"),
    ("npm registry", "https://registry.npmjs.org"),
    ("PyPI", "https://pypi.org"),
]

db = SessionLocal()
try:
    existentes = {s.nombre for s in db.query(db_models.Servicio).all()}
    agregados = 0
    for nombre, url in SERVICIOS_INICIALES:
        if nombre not in existentes:
            db.add(db_models.Servicio(nombre=nombre, url=url))
            agregados += 1
    db.commit()
    print(f"{agregados} servicios nuevos agregados ({len(existentes)} ya existían)")
finally:
    db.close()

"""Crea las tablas que falten y aplica los ajustes de esquema (índices). Es seguro correrlo muchas veces."""
import migrar

if __name__ == "__main__":
    migrar.aplicar()
    print("Base de datos lista: tablas e índices al día")

#!/usr/bin/env python
"""
Script para cargar todas las fixtures necesarias del proyecto.
Uso: python load_fixtures.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestify.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.core.management import call_command

# Fixtures a cargar
fixtures = [
    'eventos/fixtures/departamentos_ciudades.json',
    'usuarios/fixtures/tipos_documento.json',
    'eventos/fixtures/tipos_ticket.json',
]

print("🚀 Cargando fixtures...")
for fixture in fixtures:
    try:
        print(f"  📦 Cargando {fixture}...", end=" ")
        call_command('loaddata', fixture, verbosity=0)
        print("✅")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n✨ ¡Fixtures cargadas exitosamente!")

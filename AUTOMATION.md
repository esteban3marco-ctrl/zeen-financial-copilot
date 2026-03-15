# Staq/Zeen — Automation Commands

## /loop — Ciclo de desarrollo continuo

Ejecuta el ciclo completo: architect → builder → tester → siguiente módulo.

```bash
# Uso básico: continúa desde PROGRESS.md
claude -c

# Forzar módulo específico
claude --prompt "Lee PROGRESS.md, módulo: Risk Gate Framework. Ejecuta architect, luego builder, luego tester."
```

### Ciclo completo (manual)
```
1. /model opus    → architect diseña
2. /model sonnet  → builder implementa
3. Task (haiku)   → tester valida
4. Actualizar PROGRESS.md
5. Repetir con siguiente subtarea
```

## /schedule — Tareas programadas

### Lint + Tests diarios
```bash
# Ejecutar tester en todos los módulos implementados
pytest tests/ -v --cov=. --cov-report=term-missing && mypy . --strict
```

### Auto-compact
Cuando el contexto llegue al 70%, ejecutar `/compact` antes de continuar.

## Comandos de sesión

### Iniciar nueva sesión de módulo
```bash
claude --prompt "Lee PROGRESS.md. Identifica módulo en progreso. Continúa sin preguntar."
```

### Verificar estado
```bash
claude --prompt "Lee PROGRESS.md y muestra resumen del estado actual del proyecto."
```

### Ejecutar architect
```bash
claude --prompt "Eres el architect. Lee los archivos relevantes y diseña [componente]. Termina con ARQUITECTURA COMPLETA."
```

### Ejecutar builder tras diseño
```bash
# Después de que architect entregue diseño:
/model sonnet
# Luego: builder implementa según especificación
```

## Variables de entorno requeridas
```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
OPA_URL=http://localhost:8181
E2B_API_KEY=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

# src/ — Paquete Python `anonlogs`

- Toda la lógica del experimento vive aquí, con un módulo por etapa (parsing, anonymization, features, detection, evaluation, reporting).
- Los scripts y notebooks **importan** desde aquí. Si algo se usa en dos lugares, va aquí.
- Aquí no van datos, configuraciones con valores del experimento (eso va en `configs/`) ni secretos.

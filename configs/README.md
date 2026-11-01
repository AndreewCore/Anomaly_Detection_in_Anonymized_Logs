# configs/ — Configuración del experimento (YAML)

- `experiment.yaml`: parámetros fijos (rutas, partición temporal, anonimización, hiperparámetros, umbrales).
- `matrix_smoke.yaml` → prueba rápida de que el pipeline funciona; **no** produce resultados para el artículo.
- `matrix_exploracion.yaml` → fase 1: todas las combinaciones curadas, 5 semillas, para elegir finalistas.
- `matrix_confirmacion.yaml` → fase 2: solo finalistas, 30 semillas; de aquí salen las tablas del artículo.
- Aquí no van secretos (el salt va en `.env`) ni datos.

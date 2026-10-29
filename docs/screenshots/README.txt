ACI Policy Blueprint — paquete de evidencias listo para integrar
Fecha local: 2026-10-29, America/Tegucigalpa. Versión 0.1.0.
Commit de código: dfcb727d2de41ca9ee4a362613a3836c67d3a445.

images/: cinco capturas JPEG reales del navegador, 1280 × 720, revisadas visualmente.
views/: los documentos HTML estáticos capturados. Son reportes locales de resultados,
no una interfaz del producto ni de APIC. No contienen recursos externos.
runs/: comandos, stdout/stderr separados, códigos de salida y artefactos reales.
sources/: ejemplos y código pertinente, contrastados byte por byte con el commit.
captions.txt: textos listos para integrar.
portfolio-selection.json: selección recomendada 01 y 04.
manifest.json + SHA256SUMS.txt: procedencia y hashes con rutas relativas.

94 tests, lint, formato y siete ejemplos aprobados en esta ejecución local.
Los siete CLI se volvieron a ejecutar con stdout y stderr separados (direct/).
Los casos negativos terminan con código 1 esperado: no son fallos de la verificación.
No hubo APIC, EVE, Proxmox, fabric ni cambios remotos.
No se modificó el código del repositorio. Solo se escribieron evidencias en la carpeta autorizada.
El chat principal informó de un cambio documental en docs/validation.md; no se incluye
ese documento en las fuentes publicables ni se presenta como parte del commit de código.

Las rutas argv se conservan relativas al directorio original del repositorio.
Para reproducir, usar el repo indicado y reemplazar --output por una carpeta NUEVA.
PYTHONDONTWRITEBYTECODE y la desactivación de caché evitan escrituras en el repo.
El primer intento se detuvo por una ruta temporal con espacios: se conserva solo
fuera de este paquete. No se distribuyen pytest-tmp ni intentos fallidos.
Las direcciones de los ejemplos son documentación (192.0.2.0/24); no son redes privadas.
Los hashes detectan cambios de bytes, no constituyen una firma digital.

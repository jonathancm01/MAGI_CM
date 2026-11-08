# Comparar un modelo y el Consejo MAGI

El objetivo es medir resultados, no contar aprobaciones. Esta herramienta no envía prompts ni selecciona modelos.

1. Define una tarea idéntica, archivos iniciales iguales, criterios de aceptación y un presupuesto comparable. Registra modelos, instrucciones, consultas y tiempo total de generación.
2. Obtén dos resultados en carpetas distintas: uno creado por un modelo y otro por el Consejo. La ruta directa de MAGI incluye un revisor y no representa un modelo trabajando completamente solo.
3. Prepara fuera de esas carpetas scripts Python de comprobación independientes. Cada script recibe la ruta del proyecto como primer argumento y termina con código 0 si cumple el criterio. Usa scripts de confianza: se ejecutan con tus permisos y podrían modificar archivos. No dejes que los modelos modifiquen las comprobaciones durante la comparación.
4. Ejecuta las mismas comprobaciones sobre ambos resultados:

```powershell
.\.venv\Scripts\python.exe evaluate_magi.py --single C:\pruebas\individual --council C:\pruebas\consejo --check C:\pruebas\validar_requisitos.py --check C:\pruebas\validar_regresiones.py
```

El JSON muestra éxitos, fallos, salida de los scripts y segundos de cada comprobación. El límite por script es 120 segundos. No son segundos de generación ni tokens consumidos. `passed_difference` positivo significa más comprobaciones satisfechas por el Consejo; no demuestra por sí solo mejor calidad general. Conserva el informe junto a los artefactos y los criterios originales.

5. Para presentación y experiencia de uso, compara ambos resultados sin revelar cuál es cuál. Evalúa cumplimiento, claridad, accesibilidad y facilidad de uso con la misma escala. Registra también defectos y ajustes manuales necesarios. Repite varias tareas antes de sacar conclusiones sobre los modelos.

No se ha realizado aquí una comparación nueva con modelos reales. Las pruebas automatizadas de esta herramienta usan proyectos sintéticos para verificar que la comparación se ejecuta correctamente.

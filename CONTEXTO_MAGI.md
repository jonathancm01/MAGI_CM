# MAGI — Contexto y continuidad entre modelos

Última actualización: **2026-11-07, America/Guatemala**. Preparada la publicación del harness actual en el repositorio, conservando datos y proyectos locales fuera de Git.
Responsable de esta actualización: Codex. Estado: versión con tres motores, colaboración integrada, tema NERV y diagnóstico Claude; 125 pruebas pasan en la verificación previa a publicación.

## Resumen de traspaso a Claude — 2026-11-01

**Jonathan usará este mismo archivo para intercambiar el contexto entre Claude y Codex.** No crear otra copia paralela del contexto. Al recibir una nueva solicitud, leer este archivo desde disco: la versión incluida en un chat anterior puede estar desactualizada.

- **Dónde trabajar:** `C:\Users\Jonathan\Documents\ChatGPT\MAGI\MAGI_CM`, no su carpeta superior ni los proyectos generados. Rama local de desarrollo: `codex/magi-harness`; rama principal remota: `master`. El 2026-11-07 Jonathan autorizó publicar el código local del harness. Comprobar HEAD, remoto y cambios pendientes antes de trabajar; las advertencias históricas sobre código sin seguimiento describen el estado anterior a esa publicación.
- **Estado funcional:** proyectos/chats independientes, papelera recuperable, preguntas directas, rutas de trabajo, Consejo de tres núcleos, plan integrado, turnos exclusivos de escritura, revisión cruzada y correcciones limitadas. El coordinador no es un cuarto modelo.
- **Motores actuales:** Codex, OpenCode y Claude Code. Claude fue probado con su sesión local en lectura y escritura sobre datos ficticios; sus subagentes internos/customizaciones no están habilitados por MAGI. No cambiar modelos guardados para realizar tareas sobre el harness.
- **Diseño obligatorio:** MAGI centrado y prioritario; conservar intactas sus variantes Clásico/Triangular. Tema NERV solo en navegación, chat y diálogos. Chat ancho debajo, scroll propio y compositor visible que no cubra mensajes.
- **Pruebas conocidas:** la última suite funcional registrada pasó 125 pruebas el 2026-11-07. Para cambios posteriores usar `.\.venv\Scripts\python.exe -m unittest discover -q` desde el repositorio y registrar el resultado real.
- **Datos que preservar:** `.magi/`, `projects/`, `damas/`, borradores, modelos y cambios locales. `projects/LandingHCS/` existe y es un proyecto separado del usuario, no el código de MAGI. No modificarlo salvo solicitud explícita. No copiar conversaciones, datos de cuenta ni credenciales a este archivo.
- **Arranque:** `start.ps1` o el acceso directo. Cambiar Python requiere cerrar todas las pestañas y volver a iniciar; recargar el navegador no reemplaza el proceso anterior. No detener una operación activa para comprobar cambios visuales.
- **Siguiente trabajo:** Jonathan indicará qué cambios quiere que haga Claude. Este traspaso no autoriza ejecutar antiguas tareas de portafolios, cambiar el stack, publicar, desplegar ni hacer commit/push.

Al terminar cada intervención, actualizar el resumen/estado y las secciones afectadas, añadir una entrada fechada y firmada en la bitácora, y especificar qué quedó pendiente. Codex aplicará el mismo procedimiento cuando Jonathan vuelva a este chat.

## 1. Cómo usar y mantener este archivo

Este documento permite continuar el desarrollo sin disponer del chat original. Resume las solicitudes de Jonathan, las decisiones aceptadas, el código actual y sus límites. Acompáñalo del repositorio si el otro modelo no tiene acceso a sus archivos: el documento no sustituye al código.

Antes de modificar el sistema:

1. Lee este archivo y `README.md`, y después los archivos afectados.
2. Comprueba la rama, `git status --short` y el código real. Hay mucho trabajo local sin commit; no confundas el último commit con la aplicación actual.
3. Conserva las decisiones del usuario y continúa desde el estado existente. La petición humana más reciente puede cambiar estas decisiones.
4. Distingue hechos comprobados, hipótesis y propuestas pendientes. Si encuentras una diferencia con este archivo, compruébala y corrige el documento.
5. Implementa la solicitud concreta, conserva los datos y ejecuta las comprobaciones pertinentes.
6. **Antes de terminar, actualiza las secciones afectadas de este mismo archivo y añade una entrada a la bitácora.** Actualiza también el README si cambia la forma de usar o instalar MAGI.

No basta con añadir una nota al final si las secciones anteriores quedaron obsoletas. Tampoco borres decisiones o problemas que siguen vigentes. No copies credenciales, tokens, conversaciones privadas ni volcados completos de `.magi/` a este documento.

La actualización es manual: este archivo no se sincroniza automáticamente con los modelos ni se incorpora por sí solo a sus conversaciones. Jonathan lo compartirá o indicará al siguiente modelo que lo lea.

### Instrucción lista para entregar al siguiente modelo

> Continúa el desarrollo de MAGI a partir de `CONTEXTO_MAGI.md`. Léelo junto con el código antes de cambiar nada. Respeta las decisiones vigentes, conserva los datos y el trabajo local, e implementa únicamente la nueva solicitud que te indique. Comprueba el resultado y, antes de finalizar, actualiza el estado actual, las decisiones que hayan cambiado, las pruebas y la bitácora de este mismo archivo para que otro modelo pueda continuar. No presentes propuestas pendientes como funciones implementadas.

Claude y Codex deben editar el mismo archivo en el repositorio. Si ambos trabajan sobre esta carpeta, evitar modificaciones simultáneas de los mismos archivos; antes de escribir, volver a comprobar los cambios existentes. Este documento registra decisiones y evidencias, no bloquea ni coordina procesos automáticamente.

## 2. Qué es el proyecto

**MAGI = Multi Agent Group Intelligence.** Es un harness local inspirado en las supercomputadoras MAGI de *Neon Genesis Evangelion*. Jonathan quiere una experiencia de trabajo con proyectos y chats comparable a una aplicación como Codex Desktop, manteniendo la pantalla de MAGI como elemento central.

El objetivo es configurar tres núcleos con motores/modelos elegidos por el usuario, hacer que colaboren, revisen su trabajo y resuelvan condiciones dentro de límites controlados. Debe poder construir páginas y sistemas, modificar proyectos existentes y responder preguntas sencillas con poca deliberación.

Referencias proporcionadas por Jonathan:

- Fork de partida: <https://github.com/jonathancm01/MAGI_CM.git>.
- Proyecto original atribuido en el README: <https://github.com/TomaszRewak/MAGI>.
- Inspiración MAGI: <https://evangelion.fandom.com/wiki/Magi>.
- Referencias visuales aportadas mediante imágenes: diseño clásico con tres paneles y diseño triangular con cuadrados inclinados y círculo central. Ambas variantes están implementadas.

Se conserva la atribución y licencia MIT del proyecto original. Las perspectivas de los núcleos son una adaptación para desarrollo de software, no una reproducción literal de las personalidades de la serie.

## 3. Decisiones y preferencias que hay que preservar

- **MAGI tiene prioridad visual.** Debe permanecer centrado y visible; no relegarlo a un costado para dar protagonismo al chat.
- La interfaz conserva el lenguaje visual de Evangelion: fondo oscuro, naranja, tipografía existente, rótulos japoneses y los tres núcleos.
- El chat principal va **debajo de MAGI y a todo el ancho disponible**, con su propio scroll. El campo de escritura se mantiene visible, compacto y separado del historial; no debe tapar los mensajes.
- Las configuraciones se abren desde **Configuración**, en la cabecera del chat, en una ventana aparte. No deben volver a llenar la superficie bajo MAGI.
- Mantener la barra de proyectos plegable y las variantes Clásico/Triangular, con sus preferencias guardadas en el navegador.
- Reducir la carga de texto y controles visibles. Se retiraron el nombre del proyecto, título del chat, ruta y rótulo «Consejo MAGI» de encima del panel. La ruta sigue accesible en Configuración.
- El nombre del logo es MAGI y su expansión actual es **Multi Agent Group Intelligence**. El usuario escribió originalmente «Gruop»; la interfaz existente utiliza «Group».
- Las preguntas sencillas deben responderse directamente: no generar planes ni convocar tres votaciones para una explicación o saludo.
- En trabajo complejo, los otros dos núcleos deben contribuir; el coordinador no debe hacer toda la implementación mientras ellos esperan.
- La automatización debe conservar condiciones reales, límites de consultas/ciclos y cancelación. No convertir una condición o error en aprobación para que el flujo avance.
- Jonathan eligió **sesiones autenticadas de las herramientas instaladas**, en vez de empezar con API keys. MAGI usa sus CLI; no requiere un backend nuevo de API keys para funcionar.
- Evitar consumo innecesario de suscripción. No sustituir modelos por Astra ni por otro más costoso automáticamente. Un nombre disponible en Codex Desktop no garantiza que la CLI de Codex lo acepte.
- Los proyectos y chats deben conservar contexto, configuración y borradores independientes. Continuar una conversación no debe reconstruir el proyecto desde cero.
- El botón global **Nuevo chat** crea una carpeta nueva dentro de la raíz de MAGI. Al abrir una carpeta existente, los núcleos deben poder editar allí durante una ejecución autorizada.
- Eliminar chats debe seguir siendo recuperable y conservar los archivos del proyecto.
- Proponer cambios adicionales de UI antes de implementarlos cuando sean ajenos a lo pedido. No pedir confirmación repetida para los cambios que Jonathan ya autorizó.
- Preferir cambios pequeños y completos, reutilizando el código existente. Evitar migraciones de stack, dependencias, refactorizaciones o funciones sin necesidad concreta.

Una petición anterior excluyó unas propuestas denominadas «4 y 5». El contenido exacto de esa enumeración no está disponible en este contexto; no inventar cuáles eran ni considerarlas autorización para futuras funciones. El comportamiento actual está descrito a continuación.

## 4. Entorno y estado del repositorio

- Sistema de trabajo comprobado: Windows, PowerShell.
- Carpeta del espacio de trabajo de Jonathan: `C:\Users\Jonathan\Documents\ChatGPT\MAGI`.
- **Repositorio real:** subcarpeta `MAGI_CM` de ese espacio. En adelante, `<REPO>` significa esa carpeta, donde están `main.py` y `requirements.txt`.
- Rama observada: `codex/magi-harness`.
- Base histórica del fork: `98a4d01` (`Improving the prompt.`). La publicación autorizada el 2026-11-07 incorpora el harness completo en un commit posterior; consultar `git log` para su hash y `git ls-remote origin refs/heads/master` para confirmar lo publicado.
- No ejecutar reset, clean, checkout destructivo ni añadir todo indiscriminadamente. Preservar cualquier cambio local posterior a la publicación.
- Runtime comprobado: Python **3.14.7**, Dash **2.18.2**, `dash-local-react-components` **1.3.0**.
- Versiones de CLI registradas en pruebas previas: Codex **0.163.0**, OpenCode **2.0.31**. Volver a comprobarlas si se investigan incompatibilidades; no asumir que permanecen iguales.
- Claude Code **2.1.316** comprobado el 2026-11-01. Se verificaron `--restricted` y `--safe-mode`; no sustituirlos por bypass de permisos para soportar una CLI anterior.
- No se encontró un `AGENTS.md` propio ni un grafo `graphify-out/graph.json` al preparar este documento.
- En este equipo, invocar `python` desde PATH puede resolver a un alias que falla. Para trabajar con la instalación del proyecto, usar `.\.venv\Scripts\python.exe`.

La publicación incluye código, pruebas y documentación. Los datos privados y proyectos generados permanecen locales y no se transfieren al clonar. Comprobar siempre si hay cambios nuevos sin publicar.

### Configuración observada del chat seleccionado

Instantánea del chat del portafolio afectado por el bloqueo de Plan, consultada el 2026-10-19; no son valores universales ni una instrucción para sobrescribir otros chats:

| Núcleo | Motor | Modelo |
|---|---|---|
| MELCHIOR · 1 | OpenCode | `opencode/deepseek-v4.1-flash-free` |
| BALTHASAR · 2 | OpenCode | `opencode/deepseek-v4.1-flash-free` |
| CASPER · 3 | OpenCode | `opencode/glm-5.3-flash-free` |

Ejecutor: `melchior`; consenso: `majority`; automatización: `autonomous`; máximo de ciclos: 3; máximo de consultas: 24.

Son elecciones del usuario. Su presencia en el archivo de configuración no demuestra disponibilidad, acceso ni cuota actuales. Los valores predeterminados del código son distintos: unanimidad, MELCHIOR, modo `council`, 3 ciclos, 24 consultas y modelos vacíos para usar el predeterminado de cada CLI.

## 5. Arquitectura y mapa de archivos

La aplicación es **Python/Dash con componentes React locales**, abierta en el navegador. Tiene un lanzador para parecer una aplicación de un clic. No hay Electron, Tauri, servicio remoto ni instalador autónomo actualmente.

| Archivo o carpeta | Responsabilidad |
|---|---|
| `main.py` | Instancia Dash/Flask, árbol de UI, callbacks, formularios, navegación, acciones, conversación y refresco de estado. |
| `workspaces.py` | `WorkspaceStore`: proyectos, chats, borradores, papelera, importación del historial anterior y un `Harness` por chat. Valida la selección y serializa las operaciones. |
| `harness.py` | Estado del trabajo, rutas adaptativas, memoria, propuestas, votos, presupuestos, comunicación, ejecución cooperativa, revisión, correcciones, cancelación y persistencia. |
| `ai.py` | Descubrimiento de CLI, catálogo de modelos, comandos/permisos por llamada, procesos, eventos públicos, lectura de salida, clasificación de errores y cancelación. |
| `presentation.py` | Rótulos japoneses según el estado, votos legibles y bloques de texto escapados para el chat y los diálogos de cada núcleo. |
| `components/magi.js` | Composición de la pantalla MAGI y selección de variante. |
| `components/wise_man.js` | Panel interactivo de cada núcleo, nombre, modelo, estado y acceso a su historial. |
| `components/header.js`, `response.js`, `status.js` | Encabezados japoneses, recuadro de estado y datos visuales del sistema. |
| `components/modal.js` | Diálogo del núcleo con conversación, propuestas, votos y diagnósticos. |
| `assets/style.css` | Estilos base del diseño original y componentes. |
| `assets/zz-desktop.css` | Distribución de proyectos/MAGI/chat, configuración, compositor, estados y ajustes adaptables. |
| `assets/zz-nerv-shell.css` | Tema NERV limitado a sidebar, chat y diálogos: negro/ámbar, cabeceras, marcos, alertas y presupuesto segmentado. No seleccionar ni modificar la pantalla MAGI desde este archivo. |
| `assets/zzz-magi-variants.css` | Variante triangular y reglas compartidas de presentación japonesa. Se carga después de las anteriores. |
| `assets/chat.js` | Scroll y botón Últimos, búsqueda local de chats, ampliación del historial, atajos, pestañas accesibles y apertura/cierre de configuración. |
| `assets/lifecycle.js` | Conexión del navegador con el lanzador para detectar la última pestaña cerrada. |
| `launch.py` | Inicio sin consola, exclusión de instancias, apertura del navegador, salud y cierre al desconectarse las pestañas. |
| `start.ps1`, `create-shortcut.ps1` | Inicio en Windows y creación de `MAGI.lnk` en la carpeta superior a `<REPO>`. |
| `test_*.py` | Pruebas con datos temporales y modelos simulados. |
| `evaluate_magi.py`, `EVALUACION_MAGI.md` | Comparador local y protocolo para medir dos resultados con las mismas comprobaciones, sin hacer inferencias. No se ha demostrado superioridad general del Consejo con modelos reales. |
| `README.md` | Instalación y manual funcional. Mantenerlo coherente con este contexto. |
| `.cache/` | Caché local, log del lanzador, pruebas visuales y capturas. Está ignorada por Git. No es fuente canónica ni se garantiza en otra instalación. |
| `.magi/` | Datos reales de la aplicación. Está ignorada por Git. |
| `projects/` | Carpetas de los proyectos creados mediante Nuevo chat. Ignoradas por Git. |
| `damas/` | Proyecto generado del usuario existente en esta copia. **No es parte del harness y no se debe borrar, modificar ni incluir en un commit por accidente.** |

No hay un cuarto modelo orquestador obligatorio. El control del flujo lo realiza `Harness` en Python y el núcleo elegido como ejecutor actúa como coordinador de contenido.

### Puntos de entrada para cambios habituales

- Mensajes, botones y disposición: `app.layout`, `handle_action()`, `refresh()`, `conversation()` en `main.py`, más los CSS y `assets/chat.js`.
- Comportamiento al enviar: `WorkspaceStore.perform()` → `Harness.submit()` → `Harness.consult()` → respuesta o `Harness.start()`.
- Planes y ejecución: `deliberate()`, `execute()`, `cooperative_pass()`, `implementation_loop()`, `direct_loop()`, `review_again()` y `review_loop()`.
- Contexto compartido: `memory()`, `prompt()`, `broadcast()` y `exchange()`.
- Integración de herramientas: `ai.command_for()`, `run_agent()`, `parse_output()`, `live_event()` y `model_catalog()`.
- Datos: `WorkspaceStore.commit()`, `Harness.persist()`/`persist_dialogue()` y `write_json()`; esta última escribe mediante archivo temporal y reemplazo atómico.

## 6. Flujo funcional vigente

### Proyectos, conversaciones y continuidad

- **Nuevo chat global:** crea `projects/chat-<id>/`, un proyecto para esa carpeta y su chat; hereda una copia de los ajustes del chat abierto. No llama a modelos.
- **＋ junto a un proyecto:** crea otro chat sobre la misma carpeta existente. Copia los ajustes recientes de ese proyecto y después cada chat mantiene los suyos.
- **Añadir proyecto:** recibe una carpeta existente y permite trabajar directamente allí. No cambia la carpeta de un chat mediante un campo libre; se conserva su vínculo con el proyecto.
- Los chats de una misma carpeta comparten sus archivos. El aislamiento actual cubre contexto y configuración, **no copias del filesystem ni worktrees**.
- El borrador se guarda al salir del campo o cambiar de chat. La UI comprueba `view`, `session`, `composer-chat` y el identificador de ejecución para evitar enviar a otra conversación durante una transición.
- Una operación activa en toda la instancia. Se puede navegar y preparar borradores en otros chats durante ella, sin iniciar otra operación.
- Preguntar conserva tarea, plan, votos, identificadores y autorizaciones de trabajo vigentes. Las solicitudes de edición continúan desde los archivos actuales.
- Tras reiniciar no se reanudan procesos ni se recupera una autorización de escritura anterior. Las tareas interrumpidas pueden haber dejado cambios parciales.

### Modo del mensaje: `auto`, `ask`, `work`, `council`

| Selector | Comportamiento |
|---|---|
| Automático | Una llamada de lectura al coordinador responde y decide la ruta. Una pregunta sencilla termina con esa respuesta, sin llamada adicional para clasificar. |
| Preguntar | Respuesta directa de lectura, sin preparar implementación ni votar. |
| Trabajar | Evalúa el alcance: cambios pequeños y reversibles usan ejecutor + revisor; lo complejo pasa al consejo. Una pregunta sigue siendo una pregunta. |
| Consejo | En preguntas reúne tres perspectivas y una síntesis; en trabajo solicitado utiliza la deliberación de los tres. |

`parse_route()` admite `answer`, `discuss`, `work`, `council`. Las rutas de edición exigen `edit_requested: true` y un plan no vacío. Una decisión inválida produce error y no habilita escrituras. Pedir expresamente la opinión de los tres también activa la consulta conjunta en Automático.

La llamada de enrutamiento conoce el modo seleccionado y explica que su lectura sola es temporal: MAGI activa Build/workspace-write posteriormente, cuando corresponde implementar. No debe rechazar una solicitud de construcción por estar ahora en Plan ni pedir al usuario cambiar de agente. Las confirmaciones de empezar a implementar se interpretan con el contexto del chat; el selector por sí solo no convierte una pregunta en autorización. Las respuestas antiguas sobre falta de agente de edición no describen los permisos de los turnos futuros.

Las preguntas se guardan en `dialogue`, separadas de la tarea. Su contexto incluye los cuatro últimos intercambios y un extracto del trabajo activo. El contexto del trabajo usa el objetivo original y extractos de los dos últimos pasos, sin gastar una inferencia en resumirlos.

### Trabajo acotado

Un cambio pequeño no simula tres votos aprobatorios. Prepara un plan breve, utiliza un escritor y un revisor independiente, y puede corregir condiciones dentro del mismo alcance. Manual y Consejo automático requieren **Ejecutar plan**; Autónomo puede ejecutar la solicitud de edición identificada.

### Consejo completo y trabajo cooperativo

1. Tres propuestas independientes en paralelo, partiendo de la misma instantánea de mensajes.
2. El coordinador produce una síntesis explícita de las tres propuestas, con aportes incorporados/descartados, reparto por núcleo, dependencias y criterios de aceptación. Los tres votan ese mismo plan integrado. Una síntesis vacía se detiene antes del voto.
3. Consenso configurado: unanimidad 3/3 o mayoría 2/3. Un error de un núcleo impide aprobar. El modo autónomo exige aprobación sin disenso para ejecutar automáticamente, aunque se haya elegido mayoría.
4. Cuando el modo lo permite, nuevas rondas de lectura comparten objeciones y revisan propuestas. Repetir plan/objeciones sin progreso detiene el ciclo.
5. Al ejecutar, el coordinador escribe la base mientras los otros dos preparan aportes de lectura en paralelo.
6. Cada colaborador lee el resultado actual y aplica su aporte en un turno exclusivo de escritura. **No hay tres escritores simultáneos.**
7. Tres revisiones del resultado integrado, con un encargo cruzado determinista: MELCHIOR→BALTHASAR→CASPER→MELCHIOR. Se piden evidencias de archivos y comprobaciones propias, no solo repetir informes. Según el modo, se corrige y vuelve a revisar dentro del plan y presupuesto autorizados.

Cada escritor recibe su encargo del reparto incluido en el plan y debe informar encargo, aporte, archivos, verificaciones y límites. No hay aislamiento por archivo: los prompts y la revisión delimitan responsabilidades, el sandbox permite la carpeta aprobada. El plan es texto legible, no un contrato estructurado con validación automática del reparto; los votos deben bloquear reparto/criterios ausentes. No afirmar que estas instrucciones garantizan mejor calidad con cualquier modelo.

La comunicación entre núcleos es un registro de mensajes gestionado por Python e incorporado a prompts posteriores. No es una conversación espontánea entre procesos CLI ni una sesión nativa compartida. Cada llamada a una CLI es independiente; MAGI reconstruye el contexto.

Los votos usan JSON con `vote: yes|no|conditional`, `reason` no vacío y `suggestions` opcional como lista de textos. Las mejoras opcionales pueden acompañar un `yes`; requisitos incumplidos, riesgos reales y verificaciones indispensables pendientes siguen bloqueando. No degradar esta distinción para evitar rondas.

### Automatización y presupuestos

- `manual`: deliberación y ejecución explícita; no reparaciones automáticas tras la revisión.
- `council`: debate/correcciones automáticas; requiere permiso explícito con Ejecutar plan para empezar a escribir.
- `autonomous`: enviar la solicitud de trabajo autoriza implementación y correcciones dentro del alcance cuando se cumplen sus condiciones.
- Predeterminado: 3 ciclos, 24 consultas por operación; configurable entre 1–5 y 6–120, respectivamente.
- Costes base del consejo: 7 llamadas por deliberación (3 propuestas + síntesis + 3 votos), 8 por pasada cooperativa + revisión, 3 por Revisar. Antes de deliberar reserva capacidad para las 7; límite 6 sigue siendo válido para rutas directas, pero no permite consejo completo. Enrutamiento, rondas y reintentos añaden llamadas. Consulta directa normalmente 1; consulta conjunta 4.
- Las consultas son llamadas, **no un presupuesto exacto de tokens ni de suscripción**. Crear/abrir/eliminar/restaurar chats, guardar ajustes y navegar no hace inferencias.
- Cambiar la tarea/configuración invalida el plan autorizado. Un borrador sin enviar impide ejecutar accidentalmente un plan anterior.
- **Revisar** vuelve a comprobar lo terminado en lectura: no repite implementación ni activa reparaciones por sí solo.
- Cancelar detiene procesos; no deshace los archivos que ya escribieron. No hay rollback automático.

## 7. Integraciones, permisos y errores

### Codex

`codex exec --json`, sandbox `read-only` para consultas/deliberación/revisión y `workspace-write` para ejecución; aprobación no interactiva `never`. El prompt se transporta por stdin. No usar flags que deshabiliten sandbox/aprobaciones.

### OpenCode 2

`opencode run --standalone --format json`, agente `plan` o `build` según permisos. Configuración por llamada en `OPENCODE_CONFIG_CONTENT`, con esquema V2 de `permissions`/`policies`; no modifica la configuración global del usuario. Se habilitan herramientas de lectura y, al escribir, edición. Code Mode `execute` sirve para invocar herramientas permitidas. Terminal, MCP, secretos y acceso externo siguen denegados por las reglas/políticas implementadas.

Estas políticas de OpenCode **no equivalen a un sandbox del sistema operativo**. No describir la integración como aislamiento absoluto ni abrir terminal/permisos globales para resolver una condición de un agente.

### Claude Code

Motor `claude`, CLI nativa o shim npm. `--print --output-format stream-json --verbose --restricted --safe-mode --permission-mode dontAsk --permission-prompts none`, MCP vacío y estricto, sin persistencia ni comandos slash. Read/Glob/Grep en lectura; añade Edit/Write en escritura. Sin herramientas de terminal ni Agent: no importa agentes personalizados ni crea subagentes internos. Las perspectivas de MAGI siguen configurándose por núcleo. Requiere CLI reciente; no degradar quitando restricted/safe-mode para compatibilizar una versión vieja.

La CLI conserva su autenticación, sin leer credenciales desde MAGI. Se ignoran customizaciones y hooks; managed settings siguen aplicándose. Denegados secretos habituales, .git, .magi, .claude y .mcp.json. Restricted confina herramientas de archivos al directorio de trabajo. Parsear solo el resultado final exitoso; un fallo, salida incompleta o permission_denials detiene el turno. No mostrar bloques thinking. Las verificaciones que requieren terminal no están disponibles en este adaptador.

Desde 2026-11-02 los errores con permission_denials conservan nombres de herramientas y hasta 6000 caracteres del informe final; no incorporan tool_input/argumentos crudos. Claude recibe antes de planificar un aviso explícito de que Edit/Write no habilita git clone ni red. Esto permite detectar dependencias inviables antes de votar, pero no incorpora herramientas nuevas ni garantiza automáticamente un reparto ejecutable.

### Modelos disponibles

Catálogo de metadata: Codex `debug models`; OpenCode `models --standalone`. Caché de cinco minutos por herramienta/carpeta. Claude ofrece alias sonnet/haiku/opus, no enumera acceso de la cuenta; admite ID manual y modelo vacío para usar su predeterminado. Abrir Configuración o Actualizar modelos no envía prompts. La selección guardada se conserva aunque falte en la lista.

No confundir nombres visibles en otras aplicaciones con identificadores válidos de estas CLI. Hubo rechazos de `gpt-6.1-sol` en la CLI de Codex de este equipo; esto es un antecedente de compatibilidad, no una regla permanente sobre ese modelo. No resolverlo usando silenciosamente un modelo más costoso.

### Errores y reintentos

`ai.error_info()` separa cuota, modelo, autenticación, permisos, formato, fallos transitorios y otros errores CLI. La UI muestra un título entendible, una acción sugerida y detalle técnico desplegable.

- Un reintento selectivo para errores transitorios o votos mal formados **en fases de lectura**, conservando respuestas válidas de otros núcleos.
- No reintentar automáticamente cuota, acceso/modelo inexistente, autenticación o permisos.
- No repetir una escritura fallida a ciegas: pueden existir cambios parciales.
- Un error nunca cuenta como aprobación ni activa un cambio automático de modelo.
- Timeout actual de llamada a modelos: 600 segundos. Se limita la captura de salida. Las pruebas cubren terminación y cancelación de procesos.
- La actividad muestra eventos públicos de herramientas y fragmentos de respuesta cuando la CLI los emite. No mostrar razonamiento interno ni comandos completos como indicador de progreso.

La aplicación escucha en loopback y valida host/origen/tipo de contenido de las solicitudes. Es local y para un usuario, no un servicio preparado para exposición pública.

## 8. Datos que hay que conservar

```text
<REPO>/
  .magi/
    config.json                         # configuración anterior / punto de partida
    workspaces.json                     # proyectos, chats, selección, borradores, ajustes, papelera
    chats/<chat-id>/
      <task-id>.json                    # estado/historial de trabajo
      conversation/messages.json        # preguntas y respuestas independientes del trabajo
    tasks/                              # historial legado importado sin sobrescribir originales
  projects/chat-<id>/                    # archivos reales de nuevos proyectos
  damas/                                # proyecto real previo del usuario
  .cache/launcher.log                    # diagnóstico de inicio
```

La papelera marca chats como eliminados y permite restaurarlos con memoria, borrador y modelos. No elimina carpetas del proyecto ni libera definitivamente el espacio del historial. No se puede eliminar el chat ocupado; al quitar el último se crea otro chat vacío en esa carpeta. Otras pestañas con una selección borrada recuperan una selección válida sin escribir encima del borrador de otro chat.

No usar datos reales como fixtures de pruebas. No importar `main.py` en una prueba sin aislar el `WorkspaceStore`: su importación inicializa el estado de la aplicación. Los tests existentes muestran cómo parchearlo con almacenamiento temporal.

Nunca incluir `.magi/`, credenciales de CLI, `.venv/`, `.cache/` ni proyectos generados en un paquete de código por accidente. Para migrar esquemas reales, preservar los originales y comprobar recuperación/errores de almacenamiento.

## 9. Interfaz actual y último cambio aplicado

Distribución principal:

```text
Barra plegable de proyectos | MAGI centrado, visible
                           | Estado breve de la operación
                           |----------------------------------
                           | Conversación      [Configuración]
                           | Historial con scroll propio
                           |----------------------------------
                           | Modo | Mensaje...        | Enviar
```

Detalles de implementación que no hay que perder:

- `.desktop-shell` tiene sidebar + `.workspace-pane`; esta última contiene `.council-pane` arriba y `.chat-pane` abajo. Distribución habitual 55%/45%, adaptada en ventanas pequeñas/bajas.
- `.magi-stage` centra el diseño sin deformarlo. Clásico conserva proporción 2:1; triangular 1.32:1. La altura/ancho se limitan al espacio disponible.
- `#conversation` es una región con scroll y foco de teclado. Los mensajes no hacen crecer toda la página ni desplazan MAGI fuera de la vista.
- `.composer` tiene espacio reservado dentro del layout, no un overlay. Entrada inicial de 48 px, ampliable verticalmente hasta 96 px. En ventanas estrechas distribuye sus controles en dos filas.
- El selector `#request-mode` abre opciones hacia arriba para que no queden fuera de pantalla.
- `assets/chat.js` lleva al último mensaje al abrir/cambiar conversación y sigue nuevos mensajes si el usuario estaba cerca del final. Permite leer mensajes anteriores sin forzar el scroll continuamente.
- Ejecutar plan, Revisar y Detener aparecen en la cabecera cuando están disponibles; sus estados siguen gobernados por el harness. La política de edición visible usa la configuración guardada, nunca cambios pendientes del formulario.
- `#workspace-tools` es un `<dialog>` nativo con pestañas Chat y trabajo, Núcleos y Actividad. Todos los controles permanecen montados al cambiar de pestaña. Flechas/Home/End navegan entre pestañas. Guardar cambios está fuera del área de scroll; cerrar o Escape conserva el borrador.
- `#configuration-notice` muestra éxito/error dentro del diálogo. `handle_action()` devuelve aviso general, borrador, aviso de configuración y snapshot `saved-form`. Este último solo cambia después de guardar con éxito o cargar un chat.
- Enviar/ejecutar/revisar usan la configuración persistida. Solo Guardar lee el formulario. El indicador de cambios pendientes compara los campos con `saved-form`.
- `WorkspaceStore.perform(save)` permite renombrar chat/proyecto con validación de texto imprimible, no vacío y hasta 80 caracteres. Actualiza junto a la configuración de forma atómica; conserva IDs, rutas e historial. Un título personalizado no se reemplaza al enviar el primer mensaje.
- Búsqueda local sin tildes por proyecto/chat, contador y aviso sin resultados. Ctrl/Cmd+K despliega la barra y enfoca la búsqueda; Ctrl/Cmd+Enter envía y Ctrl/Cmd+, abre configuración.
- Ampliar chat reparte aproximadamente 34%/66% sin ocultar MAGI. Últimos recupera el final del historial. Los avisos de éxito se retiran tras seis segundos, los errores permanecen.
- Las zonas de navegación/chat usan Segoe UI; el panel MAGI conserva su tipografía. Controles de 44 px, foco visible y respeto a movimiento reducido. En paneles de hasta 420 px se omiten detalles secundarios de los núcleos para evitar solapamientos; siguen disponibles al abrirlos.
- Tema exterior NERV: cabeceras y botones usan fuentes condensadas locales con fallback; cuerpo de chat sigue legible en Segoe UI. Negro, ámbar, verde de confirmación y rojo de error, marcos dobles, sin estrobos ni scanlines sobre texto. Cabeceras 通信 (comunicación) y 設定 (configuración) son decorativas y aria-hidden, junto a su etiqueta española. No descargar ni asumir licencias de las fuentes del documento de referencia.
- `automation-status.children` ahora contiene texto y un `html.Progress` accesible con consultas reales y límite guardado/activo; no es un porcentaje de avance. Nueva regresión en test_app comprueba ambos límites.
- Se preservaron los IDs/callbacks de configuración y el descubrimiento de modelos. Al mover componentes, revisar también JS, selectores CSS y salidas consumidas por pruebas.
- Hay 21 combinaciones de rótulos japoneses en `COUNCIL_CAPTIONS`. Los encabezados izquierdo/derecho forman una frase, no repiten el mismo texto; el recuadro derecho muestra su propio estado breve. Traducción española en tooltip y accesibilidad. No generan inferencias.

Capturas locales más recientes: `.cache/claude-provider.png` (selector de motores, instancia aislada), `.cache/nerv-classic-after.png` y `.cache/nerv-after.png` (tema NERV con ambas variantes), `.cache/nerv-settings.png` (configuración). Las capturas `ux-after.png`/`ux-settings.png` documentan la distribución anterior al tema. Son evidencias locales y pueden no existir al clonar el remoto.

## 10. Cómo iniciar, reiniciar y probar sin gastar consultas

Ejecutar desde `<REPO>`:

```powershell
# Instalación nueva; no recrear una instalación existente sin necesidad.
uv venv
uv pip install -r requirements.txt
.\create-shortcut.ps1

# Inicio normal, sin ventana de consola.
.\start.ps1

# Inicio manual para desarrollo; no se cierra al cerrar la pestaña.
.\.venv\Scripts\python.exe main.py

# Suite con almacenamiento temporal y modelos simulados.
.\.venv\Scripts\python.exe -m unittest discover -q
```

Autenticar Codex/OpenCode/Claude en sus propias CLI cuando sea necesario (`codex login`, `opencode auth login`, `claude auth login`). MAGI no necesita leer sus credenciales. No iniciar sesiones ni cambiar modelos solo para comprobar un cambio visual.

URL habitual: `http://127.0.0.1:8050/`.

El lanzador abre el navegador predeterminado, reutiliza la instancia de este proyecto y se apaga unos ocho segundos después de cerrar la **última** pestaña de MAGI. Tiene timeout de inicio sin navegador de 45 segundos. No termina procesos ajenos si el puerto está ocupado. Los errores se registran en `.cache/launcher.log`.

Para cargar cambios de Python en una instancia iniciada con el acceso directo:

1. Comprueba que no haya una operación ejecutándose y deja que se guarden los borradores.
2. Cierra todas las pestañas de MAGI y espera a que se libere el puerto.
3. Abre `MAGI.lnk` o ejecuta `start.ps1` de nuevo.
4. Comprueba el estado real del chat, los modelos y la UI. Una simple recarga no reemplaza el proceso Python anterior.

No matar todos los procesos Python ni reiniciar una implementación activa para aplicar un cambio visual. Si se lanza un auxiliar desde PowerShell, hacerlo con ventana oculta. Una sola instancia debe escribir en cada carpeta de historial.

### Pruebas existentes

| Suite | Área principal |
|---|---|
| `test_adaptive.py` | Preguntas directas, rutas de trabajo, contexto y conservación del trabajo aprobado. |
| `test_harness.py` | Consenso, estado, autorizaciones, ejecución y persistencia. |
| `test_automation.py` | Comunicación, ciclos, correcciones, presupuestos y trabajo cooperativo. |
| `test_workspaces.py` | Proyectos/chats, carpetas, memoria, borradores, migración y papelera. |
| `test_app.py` | Callbacks y límites HTTP, navegación, borradores, guardado y avisos dentro de Configuración. |
| `test_models.py` | Catálogo, selección, adaptadores y compatibilidad de herramientas. |
| `test_presentation.py` | Votos legibles, texto escapado, mensajes y rótulos japoneses. |
| `test_launch.py` | Lanzador, pestañas, salud y cierre. |

Los auxiliares `.cache/smoke_adaptive.py`, `smoke_models.py`, `smoke_delete.py` y otros se usaron para QA local; no son tests versionados garantizados. Para cambios de UI se utilizó una instancia aislada en 8051 con datos y respuestas simulados, sin tocar los chats reales.

### Última verificación conocida

- **2026-11-07: 125 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (15,981 s) antes de publicar. Se comprobó el remoto y se revisaron los archivos a incluir; `.magi/`, `.cache/`, `.venv/`, `projects/` y `damas/` permanecen excluidos. No se hicieron inferencias reales.

- **2026-11-02: 125 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (30,824 s), incluidos diagnóstico Claude con nombres de herramientas/informe final sin argumentos crudos y límites de capacidades antes de la planificación. No se consumieron consultas reales ni se modificaron proyectos durante esta depuración.

- **2026-11-01: 123 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (18,809 s). Las regresiones nuevas verifican las opciones Claude sin inferencias, permisos por turno, protección de rutas sensibles, resultado final/error/permisos denegados y exclusión de thinking. El callback de catálogo incluye los tres motores. Inspección del índice local: solo motores Codex/OpenCode guardados, por lo que no se necesitó migrar datos del motor retirado. Sin cambios en modelos guardados.
- Selector verificado en navegador con instancia aislada y catálogos simulados: Codex/OpenCode/Claude Code aparecen en los tres núcleos; captura `.cache/claude-provider.png`. La instancia real no se reinició ni se reconfiguró. Reiniciar y guardar Claude en el núcleo deseado para utilizarlo.

- **2026-10-25, tema NERV: 120 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (16,374 s). Instancia aislada 8051 y referencia sin tema en 8053; sin llamadas reales ni cambios de datos del usuario.
- Comparación de capturas a 1280×720: el recorte de MAGI es idéntico píxel a píxel con y sin tema, tanto clásico como triangular. Evidencia local: `.cache/nerv-baseline-final.png` contra `nerv-classic-after.png`, y `nerv-triangle-before.png` contra `nerv-after.png`. No se cambiaron componentes MAGI, CSS de su panel ni variantes.
- UI comprobada: chat largo, campos/modelos, pestañas, indicador de consultas, error simulado y diálogo del núcleo; 390×844 sin desbordamiento y Guardar visible. Capturas adicionales `nerv-settings.png` y `nerv-error.png`. Es emulación, no teléfono físico. La instancia real abierta no se interrumpe; reiniciar para cargar las cabeceras/indicador nuevos de Python.

- **2026-10-25: 119 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (20,994 s). Nuevas regresiones comprueban síntesis con acceso a las tres propuestas, plan exacto sometido a voto, tres escritores con revisión ajena, rechazo de síntesis vacía y aportes visibles sin mezclar iteraciones anteriores. Se actualizaron conteos por la llamada de síntesis y los límites siguen aplicándose antes de inferir.
- `evaluate_magi.py` compara dos carpetas con los mismos scripts Python explícitos, devuelve resultados y tiempos por comprobación. Test con archivos sintéticos verifica diferencia de requisitos satisfechos, límite temporal y validación de entradas. No llama modelos ni mide automáticamente estética/calidad general. Protocolo en `EVALUACION_MAGI.md`.
- Navegador en instancia aislada 8051: plan integrado con reparto, ejecución cooperativa terminada en 8 consultas y detalle de aportes/ejecución/revisión por núcleo en Actividad. Captura `.cache/team-contributions.png`; no se guardaron cambios en chats reales ni se consumieron modelos. La instancia real que ya estaba abierta requiere reiniciarse para cargar código Python nuevo; no se interrumpió.

- **2026-10-24: 115 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` (25,406 s); `node --check assets/chat.js` pasó. Tres regresiones nuevas cubren configuración pendiente ignorada al enviar, renombrado conservando datos y rechazo atómico de nombres inválidos.
- Instancia aislada `.cache/smoke_ux.py` en 8051, con CLI/catálogos/agentes simulados: búsqueda con y sin resultados, guardado y cambios pendientes, navegación por teclado, borrador al cerrar ajustes, Ctrl+K y Ctrl+Enter, historial/Últimos, ejecución de los tres núcleos con archivo temporal, comunicación legible, error de modelo, Detener, chat nuevo y papelera/restauración.
- Navegador a 1280×720, 390×844 y 1356×577: MAGI centrado, compositor separado del historial, barra plegable, sin desbordamiento horizontal y Guardar accesible en ventanas pequeñas. Diseños clásico y triangular comprobados. Es emulación de viewport; no prueba en teléfono físico. No se hicieron inferencias reales durante esta revisión.
- Se abrió la instancia real en 8050 con los proyectos existentes: interfaz actual, tres pestañas, formulario inicialmente sin cambios pendientes y Guardar visible. No se enviaron mensajes ni se guardaron ajustes reales. La instancia de QA se cerró al terminar.

- **112 pruebas pasaron** con `.\.venv\Scripts\python.exe -m unittest discover -q` el 2026-10-19. La nueva regresión comprueba Automático/Trabajar/Consejo sobre una conversación con un bloqueo Plan antiguo: se prepara trabajo, no se escribe durante la consulta y la ejecución autorizada sí puede crear el archivo temporal.
- Comprobación real del enrutamiento con `opencode/deepseek-v4.1-flash-free` y datos ficticios: con diseño y archivos definidos devolvió `route=work`, `edit_requested=true` y reconoció la edición posterior. Ningún archivo del proyecto del usuario se modificó. Una primera muestra demasiado genérica pidió aclarar el diseño, por lo que no se toma como prueba de implementación.
- La comprobación real hizo dos consultas de lectura a ese modelo gratuito; no se enviaron conversaciones privadas. La revisión automática rechazó una prueba que pretendía reutilizar el historial real; se sustituyó por el caso sintético. No se ejecutó la implementación real del portafolio.
- **111 pruebas pasaron** con `python -m unittest discover -q` el 2026-10-18, antes de crear este documento. Los últimos ajustes posteriores fueron de CSS y se comprobaron en navegador.
- UI comprobada en Brave: historial largo, scroll independiente con MAGI/compositor fijos, preservación del borrador, apertura/cierre con Escape, foco y guardado dentro del diálogo.
- Se probaron tamaños de ventana 900×700 y 390×844; se corrigió la deformación de MAGI en ventanas estrechas. La prueba móvil fue simulada en navegador, sin teléfono físico.
- Se comprobó el selector de modo abriéndose hacia arriba y la ausencia de desbordamiento horizontal en la ventana estrecha.
- Se reinició la instancia real inactiva y se dejó abierta con la nueva UI, conservando modelos y chats. No asumir que sigue ejecutándose al leer este documento días después.
- La última tarea de UI y la creación de este archivo no consumieron inferencias de los modelos conectados.

No presentar esos resultados históricos como una ejecución nueva de tests. Registrar siempre qué se comprobó en la tarea actual.

## 11. Secuencia de evolución del proyecto

Orden de trabajo reconstruido de la conversación, no historial de commits ni fechas individuales verificadas:

1. Idea de harness con tres núcleos configurables, inspiración Evangelion y reutilización del fork con UI existente. Al principio Jonathan pidió no escribir código; después autorizó clonar y empezar.
2. Integración mediante sesiones de herramientas instaladas. Investigación de modelos rechazados y preferencia por evitar el consumo de Astra.
3. Conservación de tarea/contexto, continuación del trabajo, condiciones y revisión sin empezar todo otra vez.
4. Lanzador de un clic con navegador y cierre del puerto al cerrar la última pestaña.
5. Proyectos y chats separados, borradores y selección persistente, manteniendo MAGI como centro visual.
6. Comunicación entre núcleos, aportes cooperativos, correcciones con límites y errores/historiales legibles.
7. Rótulos japoneses dinámicos y variante triangular elegible desde el menú.
8. Catálogo de modelos de CLI con selectores y conservación de identificadores guardados.
9. Simplificación de cabecera, expansión de nombre de MAGI y barra de proyectos plegable.
10. Escritura por fase, carpeta automática por Nuevo chat y uso de carpetas de proyectos existentes.
11. Papelera recuperable para chats acumulados.
12. Enrutamiento adaptativo: preguntas sin plan, trabajo pequeño con ejecutor/revisor, consejo completo cuando corresponde, sugerencias opcionales separadas y actividad pública en vivo.
13. Chat ancho bajo MAGI, configuración en diálogo y compositor compacto persistente.
14. Creación de este documento para compartir contexto y registrar futuras modificaciones entre modelos.
15. **Último cambio funcional:** el enrutamiento inicial recibe el modo seleccionado y la política de edición futura; permite salir de conversaciones bloqueadas por confundir Plan temporal con falta permanente de permisos.

## 12. Límites y siguientes decisiones pendientes

La corrección del enrutamiento está implementada y verificada. El bloqueo histórico de «cambia de agente» y su diagnóstico del 2026-10-19 se conservan en la bitácora; no son una solicitud pendiente de crear un portafolio. Existen proyectos generados con trabajo posterior: inspeccionar su estado si Jonathan pide continuarlos, sin asumir que siguen vacíos o volver a crearlos. En este traspaso solo se autoriza actualizar el contexto; la siguiente implementación la indicará Jonathan a Claude.

Límites conocidos que pueden orientar esa conversación, sin autorizar su implementación automáticamente:

- Los motores disponibles son Codex, OpenCode y Claude Code. Otros motores requieren un adaptador real; mencionar una herramienta no la integra.
- La aplicación usa navegador local. Un empaquetado de escritorio/instalador sería un trabajo distinto y aún no existe.
- No se reanudan sesiones nativas CLI, no hay autoresumen por modelo, worktrees por chat, rollback automático ni ediciones concurrentes de los tres núcleos.
- El límite de consultas no conoce el coste exacto de suscripción/tokens. Los catálogos tampoco prueban acceso o cuota.
- Una operación global por instancia y un usuario. Exposición remota/multiusuario no está implementada.
- Persistencia en JSON local; no hay base de datos ni sincronización entre equipos.
- Las actualizaciones del contexto entre modelos dependen de que lean y mantengan este archivo.

## 13. Bitácora de continuidad

### 2026-11-07 — Codex — Publicación del harness

- Solicitud: subir la última versión de MAGI al repositorio origin, `jonathancm01/MAGI_CM`.
- Incluidos código del harness, tres adaptadores, UI NERV y variantes, persistencia, lanzador, pruebas y documentos de continuidad/evaluación. Se excluyeron datos de chats, credenciales, entorno, cachés y proyectos del usuario; se añadió damas/ al ignore.
- Base remota comprobada antes de publicar: master en 98a4d01, igual a la base local. Publicación prevista mediante commit y avance normal de master; sin force push. La confirmación del push y su hash se informa al usuario, y debe comprobarse contra Git al retomar.
- Pruebas: 125/125; revisión de diff y selección explícita de archivos. Sin ejecutar modelos ni modificar proyectos generados.

### 2026-11-02 — Codex — Diagnóstico de permisos del coordinador Claude

- Jonathan pidió depurar el nuevo chat con Claude coordinador. Se inspeccionó el estado persistido y el informe local de esa tarea, sin enviar el historial a modelos ni reejecutar implementación.
- Hallazgo: el fallo fue en Ejecución de MELCHIOR/Claude Opus, tras aprobar el plan. Ya existía content-sources.md escrito por Claude; su contenido registra que no pudo clonar la fuente porque disponía únicamente de herramientas de archivos. El encargo requería git/red, no solo escritura. El historial guardó un error genérico y perdió los nombres exactos de permission_denials; no afirmar retrospectivamente cuál fue la herramienta rechazada.
- Corregido ai.parse_output para conservar nombres únicos de herramientas rechazadas e informe final acotado, sin argumentos crudos. harness.prompt informa capacidades Claude antes de planificar y pide no asignarse entregas que dependan de terminal/red no disponibles.
- Sin ampliación de permisos, cambio de modelos, reinicio de la instancia ni edición de la carpeta del usuario. El bloqueo de la tarea original sigue necesitando disponer de la copia local del repositorio o un mecanismo autorizado para obtenerla; no se resolvió fabricando datos o aprobando el error.
- Nuevas regresiones: diagnóstico útil sin tool_input y límites explícitos en prompts de lectura/escritura. Reiniciar MAGI para cargar el código nuevo; no se repite una escritura fallida automáticamente.

### 2026-11-01 — Codex — Traspaso documental a Claude

- Solicitud: poner al día el contexto para que Claude modifique MAGI y devuelva sus avances por este mismo archivo.
- Contrastado hoy: rama, HEAD, estado Git, mapa de archivos, motores disponibles, flags Claude, síntesis del plan, revisión cruzada, vista de aportes y carpetas de proyectos existentes. El código local y este documento siguen sin commit; no asumir que están publicados.
- Añadido resumen de traspaso al inicio, instrucciones de lectura desde disco y actualización recíproca Claude/Codex. Corregida la nota antigua del portafolio y la referencia a las últimas capturas. Añadido comparador al mapa y versión Claude al entorno.
- Archivo modificado en esta intervención: únicamente `CONTEXTO_MAGI.md`. No se modificaron datos, modelos, permisos ni código funcional; no se reinició la aplicación ni se consultaron modelos.
- Verificación documental y revisión del diff. No se repitieron tests funcionales: la última suite registrada sigue siendo 123/123 de la integración Claude, no un resultado nuevo de este traspaso.
- Pendiente: la nueva solicitud que Jonathan dará a Claude. Claude debe actualizar las secciones afectadas y añadir su propia entrada con pruebas, límites y trabajo restante antes de devolver el proyecto.

### 2026-11-01 — Claude Code como motor

- Añadido Claude Code al selector, detección, opciones de modelos, ejecución, parseo de resultados y actividad. Retirado el motor descartado del código, interfaz y documentación, sin reemplazar modelos guardados ni tocar historiales.
- Validación real: CLI 2.1.316, sesión existente; dos llamadas breves Haiku verificaron escritura y lectura de magi-test.txt en una carpeta ficticia .cache/claude-probe-*. No se enviaron chats privados ni se modificaron proyectos. El auxiliar local .cache/probe_claude.py no es parte de la suite distribuida.
- Referencia: https://code.claude.com/docs/en/cli-reference y https://code.claude.com/docs/en/permissions. No usar bare: desactiva OAuth. Restricted y safe-mode conservan autenticación y limitan herramientas/customizaciones.

### 2026-10-25 — Tema de consola NERV, preservando MAGI

- Jonathan autorizó adaptar el documento visual aportado después de analizarlo, con prohibición expresa de cambiar la pantalla MAGI. Se aplicó el estilo solo a navegación, chat, formularios y diálogos.
- Tema aislado en `assets/zz-nerv-shell.css`; dos acentos japoneses accesibles en cabeceras y un indicador segmentado de presupuesto real en `main.py`. Se preservan IDs, layout y operaciones. Sin fuentes/dependencias nuevas.
- Verificación: 120 pruebas, comparación visual de ambos diseños MAGI idénticos en píxeles y comprobación de lectura/formularios/errores en navegador. README actualizado. No afirmar fidelidad histórica exacta de colores o tipografías: es una adaptación del documento, no una reconstrucción archivística.

### 2026-10-25 — Colaboración orientada a entregables

- Solicitud: aprovechar a los tres modelos para producir mejores resultados, combinando sus propuestas en vez de escoger directamente la del coordinador.
- Cambios: síntesis del plan antes del voto, encargos separados y criterios de aceptación, informes con evidencia, revisión cruzada determinista y detalle por núcleo en Actividad. Preguntas sencillas y ruta directa siguen conservando sus llamadas y permisos anteriores.
- Comparación: herramienta local y protocolo para ejecutar las mismas verificaciones sobre resultados de uno y tres modelos. Se probó con datos sintéticos; no hay evidencia experimental nueva de superioridad de modelos reales.
- Archivos: `harness.py`, `main.py`, suites afectadas, `evaluate_magi.py`, `test_evaluate_magi.py`, README, protocolo y este contexto. Sin migración de datos, cambios de modelos ni ampliación de permisos. Reiniciar MAGI para cargar Python nuevo.

### 2026-10-24 — Comodidad general de la aplicación

| Antes | Ahora | Motivo |
|---|---|---|
| Lista larga de chats sin filtro | Búsqueda inmediata y Ctrl+K | Localizar conversaciones sin recorrerlas todas |
| Configuración extensa en una sola vista | Tres pestañas, opciones avanzadas plegadas y Guardar fijo | Reducir carga visual y desplazamientos |
| Campos pendientes podían influir al enviar | Solo se aplican al guardar, con indicador de pendientes | Hacer predecibles los permisos y modelos utilizados |
| Historial con espacio rígido | Ampliación reversible y botón Últimos | Leer y volver al final sin perder MAGI |
| Títulos generados difíciles de organizar | Renombrado de chat/proyecto sin mover archivos | Mantener una navegación reconocible |

- Archivos: `main.py`, `workspaces.py`, `assets/chat.js`, `assets/zz-desktop.css`, `test_app.py`, README y este contexto. No se cambiaron adaptadores ni lógica de consenso/edición del harness.
- Datos: no hay migración; se conservan estructura, IDs, carpetas, borradores y modelos del usuario. QA utiliza solo `.cache/`.
- Verificación: 115 pruebas y flujos de navegador descritos arriba. Los auxiliares/capturas de `.cache/` son evidencia local, no forman parte del remoto.

### 2026-10-18 — Base de continuidad creada por Codex

- **Solicitud:** disponer de un archivo con el contexto del sistema para que otro modelo continúe y lo actualice después de hacer cambios.
- **Cambios:** creación de `CONTEXTO_MAGI.md` y enlace desde el README. Sin cambios funcionales en la aplicación.
- **Inventario contrastado:** stack y versiones locales de Python/Dash, configuración seleccionada sin credenciales, rama/estado Git, módulos principales, flujo de trabajo, layout, scripts de inicio y suites existentes.
- **Validación de esta tarea:** revisión de coherencia con el código y comprobación documental; no se volvió a ejecutar la suite funcional por ser un cambio de documentación. El último resultado funcional conocido es 111/111.
- **Pendientes:** ninguna implementación nueva aprobada; esperar la siguiente solicitud. Mantener los límites de la sección 12 visibles.

### 2026-10-19 — Codex — Desbloqueo de Plan en el enrutamiento

- **Solicitud:** investigar por qué los núcleos piden cambiar a un agente de edición aun después de elegir Trabajar para implementar un portafolio.
- **Causa comprobada:** `Harness.consult().ask()` tenía un prompt distinto al de `Harness.prompt()`: anunciaba SOLO LECTURA sin explicar la edición posterior y omitía el modo de solicitud seleccionado. El coordinador devolvía `answer`, el modo Consejo reunía/sintetizaba esas negativas y nunca se creaba una tarea. El historial reforzaba el bloqueo.
- **Cambios:** `harness.py` comunica el modo, el carácter temporal de Plan, la transición posterior a Build/workspace-write y la interpretación contextual de confirmaciones de implementar. No se cambiaron permisos CLI, aprobación, modelos, datos ni respuestas existentes. `test_adaptive.py` añade una regresión para los tres modos; README y este contexto explican el comportamiento.
- **Validación:** la nueva prueba falló en los tres modos antes del arreglo; la suite completa pasó después (112 pruebas). Dos consultas reales de lectura con datos sintéticos al modelo gratuito; la muestra con diseño definido se encaminó a trabajo sin pedir un cambio de agente ni escribir archivos.
- **Privacidad y límites:** la prueba con historial real fue rechazada por revisión automática y no se ejecutó; se usaron exclusivamente datos ficticios para las llamadas de comprobación. No se implementó ni verificó el portafolio real. Los procesos OpenCode de las primeras consultas históricas también registraron un fallo de inicio standalone; no se alteró ese adaptador y las consultas reales de diagnóstico posteriores sí respondieron.
- **Continuidad:** se reinició la instancia inactiva mediante su cierre normal y se comprobó la recuperación del mismo chat, historial y modelos. Se restauró el selector Trabajar y se dejó el borrador vacío; no se envió una instrucción nueva. Jonathan puede enviar «Implementa el portafolio acordado con placeholders en index.html y styles.css». En Manual/Consejo automático siguen aplicando el botón Ejecutar y sus validaciones; Autónomo sigue sus reglas de autorización. Captura local: `.cache/magi-permissions-ready.png` (las respuestas visibles son históricas).
- **Secciones actualizadas:** estado, configuración observada, rutas, verificación, secuencia y pendientes. El auxiliar `.cache/probe_permission_routing.py` es local/ignorado, no un test versionado ni una garantía de otra instalación.

### Plantilla para la siguiente entrada

```text
### AAAA-MM-DD — Autor/modelo — Cambio concreto

- Solicitud del usuario:
- Estado antes y comportamiento resultante:
- Archivos modificados:
- Decisiones nuevas o sustituidas, y por qué:
- Datos/configuración migrados o afectados:
- Comprobaciones ejecutadas y resultado exacto:
- Qué NO se verificó, fallos o riesgos restantes:
- Próximo paso autorizado / pendientes sin autorización:
- Secciones de este documento actualizadas:
```

La bitácora debe explicar el resultado y permitir continuar, no volcar toda la conversación. Si una tarea queda incompleta, indicar el punto exacto y qué falta, sin marcarla como terminada.

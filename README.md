# MAGI CM

Harness local de tres agentes inspirado en las supercomputadoras MAGI de *Neon Genesis Evangelion*. Parte de [TomaszRewak/MAGI](https://github.com/TomaszRewak/MAGI) y conserva su interfaz de Evangelion.

Para continuar el desarrollo con otro modelo, leer y mantener [CONTEXTO_MAGI.md](CONTEXTO_MAGI.md): decisiones del usuario, arquitectura, estado actual, pruebas y bitácora de cambios.

MAGI (Multi Agent Group Intelligence) ocupa la parte superior del espacio de trabajo. La conversación usa todo el ancho debajo de MAGI y tiene su propio scroll; el campo de escritura permanece visible sin cubrir los mensajes. Los proyectos y chats están a la izquierda y el botón junto al logo pliega o restaura esa barra; la preferencia se conserva en el navegador. **Configuración**, en la cabecera del chat, abre los modelos, la automatización, el estado de los núcleos y el contexto en una ventana aparte. Se cierra con **Cerrar** o **Esc**. El chat seleccionado queda marcado en la barra lateral.

Cada núcleo tiene un motor, modelo e instrucciones independientes:

- **MELCHIOR · 1:** corrección técnica, evidencia y arquitectura.
- **BALTHASAR · 2:** estabilidad, protección de datos y mantenimiento.
- **CASPER · 3:** intención del usuario, experiencia y alternativas creativas.

Estas perspectivas son una adaptación para software y pueden editarse. Un núcleo puede usar el mismo motor que otro con un modelo distinto.

## Iniciar en Windows

Requiere Python y las CLI que quieras conectar. La interfaz usa Dash y componentes React y se abre en el navegador predeterminado.

```powershell
uv venv
uv pip install -r requirements.txt
.\create-shortcut.ps1
```

Después, abre **MAGI.lnk**, creado en la carpeta que contiene el repositorio. Puedes copiar ese acceso al escritorio o anclarlo a Inicio. Inicia MAGI sin consola y abre [MAGI local](http://127.0.0.1:8050) en una pestaña. También puedes usar `.\start.ps1`.

- Al cerrar la **última pestaña de MAGI**, el servidor se detiene y libera el puerto después de unos ocho segundos. Si había una operación, solicita cancelar las CLI y guarda su estado; los cambios escritos permanecen.
- Recargar la página conserva el servidor. Si abres varias pestañas, permanece activo mientras alguna siga conectada.
- Abrir de nuevo el acceso directo reutiliza la instancia existente. Si otro programa o una instancia manual ocupa el puerto, muestra un aviso y no termina ese proceso.
- Si el navegador no llega a conectar, el lanzador se apaga a los 45 segundos. Los errores de inicio se muestran en una ventana y en `.cache/launcher.log`.
- Si mueves el repositorio o recreas `.venv`, vuelve a ejecutar `create-shortcut.ps1` para actualizar las rutas del acceso.

Para desarrollo manual puedes iniciar con `.\.venv\Scripts\python.exe main.py`: ese modo mantiene el servidor abierto hasta detenerlo desde la terminal. El lanzador usa el código actual cada vez que vuelve a iniciarse; para probar una mejora, cierra todas las pestañas de MAGI, espera el cierre y vuelve a abrir el acceso.

MAGI reutiliza la autenticación de cada CLI, sin leer ni guardar sus credenciales. Autentica las herramientas de antemano en tu terminal:

```powershell
codex login
opencode auth login
claude auth login
```

En la barra lateral, usa **Añadir proyecto** para abrir una carpeta existente mediante su ruta absoluta. En **Configurar este chat**, elige el motor, identificador exacto del modelo e instrucciones de cada núcleo. Un modelo vacío usa la configuración de la CLI. Los identificadores disponibles en una app pueden diferir de los admitidos por su CLI; un error de acceso se muestra sin cambiar de modelo automáticamente. Para OpenCode, el formato es `provider/model`; consulta `opencode models --standalone` en OpenCode 2.

Al abrir **Configurar este chat**, MAGI detecta Codex, OpenCode y Claude Code. **Actualizar modelos** vuelve a consultar metadata. Codex utiliza `codex debug models`; OpenCode 2 utiliza `opencode models --standalone`. Sus catálogos se guardan en memoria durante cinco minutos por herramienta y carpeta; si fallan se conserva la lista previa. Claude muestra los alias **Sonnet, Haiku y Opus**, y admite un ID manual: no es un catálogo de acceso de tu cuenta. Abrir estos selectores no envía prompts.

El catálogo refleja lo que informa la CLI, no una prueba de acceso o de cuota para cada modelo. Los modelos guardados que falten en la lista permanecen seleccionados. Para usar otro identificador, escríbelo en la búsqueda y elige **Usar ID manual**; si no hay catálogo o falta la herramienta, la interfaz explica cómo revisarlo sin elegir otro modelo por ti. Cambiar de motor actualiza las opciones sin modificar la configuración guardada del chat hasta pulsar **Guardar cambios**.

**Guardar cambios** afecta al chat abierto. El índice de proyectos, los ajustes de cada chat y sus borradores se guardan en `.magi/workspaces.json`. Cada conversación tiene su propio historial en `.magi/chats/<id>/`. Todo `.magi/` está excluido de Git. La configuración anterior de `.magi/config.json` sirve como punto de partida para proyectos nuevos. Las CLI pueden conservar sus propios historiales. MAGI no copia sus credenciales al historial.

## Proyectos, chats y contexto

### Uso cómodo del espacio

La navegación, el chat y los diálogos usan un tema de consola NERV: fondos negros, marcos ámbar, cabeceras condensadas, etiquetas técnicas y alertas con borde doble. El cuerpo de los mensajes conserva su tipografía de lectura. Los acentos japoneses de cabecera llevan texto español; no hay estrobos, telemetría inventada ni fuentes descargadas. La pantalla MAGI mantiene intactos sus diseños clásico y triangular.

- Busca por nombre de proyecto o chat desde la barra lateral; la búsqueda ignora tildes. **Ctrl/Cmd + K** abre la barra y enfoca la búsqueda.
- MAGI permanece centrado arriba. **Ampliar chat** da más altura al historial; **Restaurar MAGI** recupera la distribución habitual. **↓ Últimos** permite volver al final después de leer mensajes anteriores.
- **Configuración** se divide en **Chat y trabajo**, **Núcleos** y **Actividad**. Puedes renombrar el chat y el proyecto sin mover sus carpetas. El nombre del proyecto se comparte entre sus chats.
- En **Actividad**, la barra segmentada representa consultas utilizadas respecto al presupuesto de la operación, no porcentaje de avance del trabajo.
- Los ajustes se aplican únicamente al pulsar **Guardar cambios**. El indicador **Cambios sin guardar** permite distinguir el formulario de la configuración vigente. Los límites y las instrucciones avanzadas están plegados inicialmente.
- **Ctrl/Cmd + Enter** envía el mensaje; Enter inserta una línea. **Ctrl/Cmd + ,** abre Configuración y Escape cierra el diálogo. El envío vacío se deshabilita.
- La cabecera del chat indica si habrá lectura, edición con confirmación o edición al enviar. Bajo MAGI aparece el número de consultas de la operación. **Detener** solicita cancelar los modelos; conserva los archivos ya escritos.

- **Proyectos:** cada entrada corresponde a una carpeta local. Añadir de nuevo la misma carpeta abre el proyecto existente.
- **Nuevo chat:** crea una conversación y su carpeta vacía en `projects/chat-<id>/`, dentro de la raíz de MAGI. Hereda los modelos y ajustes del chat abierto. No consulta modelos. Las carpetas generadas están excluidas del Git de MAGI.
- **＋ junto al proyecto:** crea otro chat con contexto independiente dentro de la misma carpeta del proyecto. Hereda una copia de su configuración más reciente; después sus ajustes son independientes. **Añadir proyecto** permite trabajar directamente en una carpeta existente, conservando sus archivos.
- **Enviar:** el primer mensaje da título al chat. Las preguntas conservan la tarea activa; las solicitudes de trabajo fijan o continúan su objetivo desde los archivos actuales. Para otro objetivo independiente, crea otro chat.
- **Cambiar de chat:** recupera su conversación, modelos y borrador sin inferencias. El borrador se guarda al salir del campo o cambiar de chat. Puedes navegar y preparar otro mensaje mientras un chat trabaja; la barra lateral lo marca como **Trabajando**. Se permite una operación activa a la vez.
- **Eliminar chat:** pulsa **×** junto a su nombre para enviarlo a **Papelera**. Desaparece de la lista y puedes recuperarlo con **Restaurar**, conservando historial, borrador y modelos. No se borran carpetas ni archivos del proyecto, y no consume consultas. Un chat trabajando no se puede eliminar. Al eliminar el último queda un chat vacío en la misma carpeta. Las otras pestañas que lo tenían abierto cambian a un chat disponible. La papelera es recuperable; no borra definitivamente el historial ni libera su espacio en disco.
- **Revisar:** repite únicamente las tres revisiones de una implementación terminada, con permisos de lectura. No vuelve a implementar ni requiere reescribir la solicitud.
- **Reabrir MAGI:** conserva proyectos, chats y selección. Cada pestaña mantiene su selección durante su sesión. Un plan recuperado tras reiniciar debe volver a deliberarse antes de ejecutar; nunca se recupera su autorización anterior.

Los historiales anteriores de `.magi/tasks/` se importan automáticamente como chats, agrupados por su carpeta. Se conservan los archivos originales sin sobrescribirlos. Los nuevos mensajes se guardan en el historial separado de cada chat.

La separación de contexto corresponde a mensajes, planes, votos, borradores y configuración. **Los chats de un mismo proyecto comparten los archivos de esa carpeta**; no se crean worktrees ni copias de los archivos.

La memoria compartida se construye con el objetivo original y extractos de los dos últimos pasos, sus planes, informes y veredictos. No añade una inferencia de resumen. El historial completo permanece en disco y en los diálogos de cada núcleo. Cada consulta sigue siendo una llamada independiente a la CLI: MAGI aporta el contexto y no reanuda sesiones nativas de las herramientas.

Si la aplicación se interrumpe durante una operación, la marca como interrumpida y no la reinicia automáticamente. Puede haber cambios parciales: revísalos antes de continuar. Un error de guardado se muestra en pantalla; si ocurre antes de iniciar una operación, esta no comienza.

## Cómo trabaja el consejo

El selector junto al mensaje ofrece **Automático**, **Preguntar**, **Trabajar** y **Consejo**:

- **Automático:** el núcleo coordinador responde en una sola consulta si es una pregunta. En esa misma llamada decide si una solicitud explícita de editar archivos necesita trabajo acotado o consejo completo. No hay una llamada adicional de clasificación para las preguntas sencillas. Una decisión inválida se muestra como error y nunca habilita escrituras.
- **Preguntar:** una respuesta directa en lectura sola, sin plan ni votación. Puedes pedir explicaciones del proyecto, del plan o de lo realizado. Conserva la tarea, los votos, sus autorizaciones y su progreso. Durante otra operación hay que esperar o cancelarla.
- **Trabajar:** evalúa el alcance solicitado; un cambio pequeño y reversible usa un ejecutor y un revisor independiente. Las tareas complejas pasan al equipo completo. Si el mensaje solo pregunta o necesita aclaraciones, responde sin crear un proyecto. Este modo no fuerza escrituras ante una pregunta.
- **Consejo:** para preguntas reúne tres perspectivas y una síntesis, sin plan ni implementación. Para trabajo solicitado conserva la deliberación y los votos de los tres. También puedes pedir expresamente las opiniones de los tres en Automático.

La consulta inicial identifica tu intención en lectura sola y conoce el modo seleccionado. MAGI habilita la edición en los turnos de implementación autorizados; no tienes que cambiar manualmente entre Plan y Build en la CLI. Instrucciones como «comienza a trabajar» pueden retomar el diseño solicitado en el mismo chat, aunque una respuesta anterior haya indicado erróneamente que faltaba un agente de edición. El selector por sí solo no autoriza cambios cuando el mensaje es una pregunta.

Los cambios acotados requieren **Ejecutar plan** en Manual y Consejo automático; Autónomo puede aplicarlos tras identificar la solicitud de edición. No simulan tres votos aprobatorios. El revisor comprueba el resultado y puede exigir correcciones dentro del mismo alcance. Los errores de escritura no se repiten a ciegas. Los trabajos complejos mantienen el consenso configurado antes de escribir.

Las sugerencias opcionales se registran aparte y no requieren otra ronda si el núcleo aprueba lo solicitado. Los riesgos reales, requisitos incumplidos y verificaciones indispensables pendientes siguen bloqueando: MAGI nunca convierte un voto condicional en aprobación.

Las consultas se guardan separadas de la tarea en `.magi/chats/<id>/conversation/messages.json`; reabrirlas no consulta modelos ni reanuda acciones pendientes. Los últimos cuatro intercambios y un extracto del trabajo activo dan contexto a las preguntas. Los archivos del proyecto se consultan solo cuando la pregunta lo requiere.

Durante una llamada se muestra la actividad de las herramientas y los fragmentos de respuesta que emita la CLI. Los núcleos no convocados quedan disponibles como apoyo; MAGI permanece en el centro. La granularidad depende del motor: no todas las CLI publican cada token o el nombre de cada archivo. Nunca se muestran cadenas internas de razonamiento ni comandos completos como indicador de actividad.

El botón **Diseño: Clásico / Triangular ⇄** del menú cambia la pantalla central MAGI sin interrumpir operaciones ni alterar chats o modelos. La variante triangular reproduce los tres paneles cuadrados, las inclinaciones y el círculo central de la referencia. La elección se conserva en ese navegador al recargar y al abrir otros chats.

Ambas vistas usan 21 combinaciones de rótulos japoneses según la fase real, incluyendo preguntas, respuestas y cambios acotados preparados. Los dos encabezados forman una frase y el recuadro derecho muestra un estado breve. Pasa el puntero por ellos para ver su traducción al español; también está disponible para lectores de pantalla. Estos cambios de presentación no consultan modelos.

1. **Enviar / Continuar:** los tres núcleos elaboran propuestas independientes en paralelo.
2. El coordinador sintetiza **un plan integrado a partir de las tres propuestas**: qué incorpora, qué descarta, encargos diferentes por núcleo, dependencias y criterios de aceptación. Los tres votan sobre esa misma síntesis, incluido el reparto. Un voto puede aprobar, rechazar o imponer condiciones.
3. Con unanimidad se necesitan tres aprobaciones; con mayoría, dos. Un error de cualquier núcleo impide aprobar incluso con mayoría.
4. En modo automático, comparten las objeciones y elaboran propuestas revisadas en nuevas rondas de solo lectura. Si se repiten el plan y sus objeciones, paran por falta de progreso.
5. **Ejecutar plan:** autoriza crear carpetas y crear o editar archivos dentro del plan y carpeta aprobados. MAGI comprueba primero que la carpeta admite escritura y cambia los permisos de la CLI para cada turno. El coordinador implementa la base mientras los otros dos preparan sus aportes en paralelo. Después, cada colaborador lee los cambios actuales y aplica su aporte en un turno exclusivo de escritura. No hay tres procesos editando a la vez. Cambiar la tarea o configuración invalida la aprobación; un borrador sin enviar impide ejecutar el plan anterior.
6. Los tres revisan el resultado integrado y tienen un objetivo de revisión cruzada: MELCHIOR revisa especialmente a BALTHASAR, BALTHASAR a CASPER y CASPER a MELCHIOR. Deben citar archivos y comprobaciones observadas. En modo automático pueden corregir condiciones dentro del mismo plan, sin recrear el proyecto. Sus votos no sustituyen las pruebas ni garantizan corrección.

## Automatización y comunicación

En **Configurar este chat → Automatización** hay tres modos:

- **Manual:** una deliberación; requiere **Ejecutar plan** y muestra la revisión sin aplicar correcciones automáticas. La ejecución sigue siendo cooperativa.
- **Consejo automático** (predeterminado): debate objeciones y vuelve a votar; requiere **Ejecutar plan** para escribir. Después del permiso, el equipo puede corregir y revisar dentro del alcance ya aprobado.
- **Autónomo:** **Enviar / Continuar** autoriza también implementar el objetivo cuando los tres aprueban sin condiciones. Continúa con las correcciones y revisiones permitidas. Un plan con disenso no se ejecuta automáticamente, aunque reúna la mayoría configurada.

El límite predeterminado es **3 ciclos y 24 consultas por operación**, configurable entre 1–5 ciclos y 6–120 consultas. En modo autónomo, deliberación, ejecución y correcciones comparten el mismo presupuesto. Al pulsar **Ejecutar** manualmente comienza un nuevo presupuesto para esa operación. Cada reintento cuenta. Antes de escribir se comprueba que quede capacidad para una pasada completa del equipo y revisión (8 consultas). La aplicación muestra consultas, ciclo y correcciones realizadas. Un límite de consultas no es un presupuesto exacto de tokens ni de suscripción.

Cada núcleo publica aportes, votos e informes en un registro de mensajes del chat. MAGI entrega a los demás extractos de los mensajes recientes en la siguiente ronda o turno; no usa sesiones nativas persistentes ni comunicación directa entre procesos CLI. Las tres propuestas de cada ronda parten de la misma instantánea de mensajes. El objetivo original y los últimos dos pasos también siguen disponibles como memoria.

Abre **Comunicación entre núcleos** para consultar el intercambio, o pulsa un núcleo para ver mensajes enviados y recibidos, con fase, ciclo y veredicto. Los votos antiguos en JSON también se muestran como etiquetas y justificaciones. Los textos se renderizan como bloques escapados: párrafos, títulos, listas y código, sin ejecutar HTML ni cargar imágenes remotas.

Los fallos de conexión o tiempo y los votos mal formados reciben **un reintento del núcleo afectado en solo lectura**, conservando las respuestas válidas. No se reintentan automáticamente modelos inexistentes, autenticación, cuotas ni permisos; se muestra una acción concreta y el detalle técnico. Una escritura fallida tampoco se repite a ciegas: puede haber cambios parciales y se detiene. Un fallo nunca se convierte en un voto aprobatorio ni se sustituye por otro modelo.

Haz clic en cada núcleo para consultar propuestas, votos, ejecución y revisión. **Cancelar** detiene las CLI activas; los cambios que ya se hayan escrito permanecen en disco. No hay rollback automático.

Cada deliberación realiza **7 consultas** (3 propuestas, 1 síntesis y 3 votos); con límite 6, el Consejo se detiene antes de consumir llamadas. Una pasada de ejecución cooperativa y revisión realiza **8** (1 escritura + 2 preparaciones en paralelo, 2 turnos de escritura y 3 revisiones). Revisar realiza solo 3 consultas y nunca activa reparaciones, incluso en autónomo. El enrutamiento, las rondas y los reintentos añaden consultas hasta el límite.

En **Configuración → Actividad → Aportes y verificaciones** puedes leer por núcleo la síntesis, preparación, ejecución y revisión de la iteración actual. Los informes deben separar encargo, aporte, archivos, pruebas ejecutadas y pendientes. Son informes de los modelos, no una certificación automática. El reparto está en el plan aprobado y en los prompts; los permisos siguen acotados a la carpeta, no a archivos exclusivos por agente.

Para comparar resultados de uno y tres modelos con las mismas comprobaciones, consulta [EVALUACION_MAGI.md](EVALUACION_MAGI.md). No se ejecutan inferencias adicionales automáticamente.

## Integraciones y límites

| Motor | Estado | Permisos |
|---|---|---|
| Codex CLI | Integrado | Sandbox `read-only` al deliberar y revisar; `workspace-write` al ejecutar. Las solicitudes que requieran aprobación se deniegan en este flujo no interactivo. |
| OpenCode 2 | Integrado | Instancia privada por llamada. Configuración V2 en `OPENCODE_CONFIG_CONTENT`, sin cambiar ajustes globales. Lectura al deliberar y revisar; edición al ejecutar. Code Mode puede llamar las herramientas permitidas. Terminal, MCP, secretos y acceso fuera de la carpeta permanecen denegados mediante reglas y políticas. |
| Claude Code CLI | Integrado; probado localmente con 2.1.316 | `--restricted`, `--safe-mode`, lectura con Read/Glob/Grep y edición con Edit/Write solo en turnos autorizados. Sin terminal, agentes internos ni MCP. Sesión autenticada de la CLI; sin persistencia de conversaciones CLI. |

MAGI no utiliza flags para saltarse sandbox o aprobaciones. Las políticas de herramientas de OpenCode no son un aislamiento del sistema operativo. Los permisos y extensiones del motor siguen siendo relevantes: usa proyectos de confianza y revisa las modificaciones.

La lectura sola de una deliberación es temporal: los núcleos evalúan la ejecución posterior con escritura. No necesitan pedir al usuario cambiar de Plan a Build. Un chat antiguo bloqueado por esa confusión debe volver a deliberarse con **Continuar**; actualizar MAGI no ejecuta tareas pendientes automáticamente. Si Windows impide escribir en la carpeta, MAGI muestra el error antes de iniciar la implementación.

La aplicación escucha solo en `127.0.0.1:8050` y rechaza hosts y orígenes ajenos. Es una aplicación local para un usuario: permite navegar por varios chats y comparte una operación activa entre sus pestañas. Debe ejecutarse una sola instancia por carpeta de historial. No incluye servicio multiusuario, empaquetado de escritorio ni edición simultánea en worktrees.

Para usar Claude, abre **Configuración → Núcleos**, selecciona **Claude Code** en uno o varios núcleos, elige modelo y pulsa **Guardar cambios**. Un modelo vacío usa el predeterminado de la CLI. No se cambia ningún núcleo automáticamente. Requiere una CLI reciente con los flags indicados; si no los admite, actualízala antes de usarla. MAGI conserva sus perspectivas y coordina las llamadas: no importa agentes personalizados de Claude ni habilita sus subagentes internos, para conservar los límites de consultas. Las comprobaciones que necesiten terminal deben realizarse fuera de este adaptador. No se modifican los permisos o ajustes globales de Claude.

**Un turno de escritura de Claude no habilita Git ni acceso web.** Para trabajar desde un repositorio remoto necesita una copia local obtenida previamente por un medio autorizado. El plan debe contemplar esa dependencia antes de aprobarse. Si la CLI rechaza una herramienta, el detalle muestra su nombre y el informe final de Claude; se conservan los cambios parciales y no se repite el turno automáticamente.

Referencias: [Codex no interactivo](https://developers.openai.com/codex/noninteractive), [OpenCode CLI](https://docs.opencode.ai/docs/cli/), [permisos de OpenCode](https://docs.opencode.ai/docs/permissions/), [Claude CLI](https://code.claude.com/docs/en/cli-reference), [permisos de Claude](https://code.claude.com/docs/en/permissions).

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Las pruebas verifican consenso, objeciones compartidas, correcciones automáticas, trabajo paralelo con escritura exclusiva, presupuestos, reintentos selectivos, errores legibles, votos inválidos, cancelación, ejecución explícita/autónoma, autorizaciones obsoletas, persistencia y migración, proyectos y modelos por chat, aislamiento de la memoria, navegación durante operaciones, borradores, recuperación, revisión sin escrituras, errores de almacenamiento, transporte de prompts sin shell, timeout de procesos y límites HTTP. Usan agentes simulados; no consumen inferencias.

Licencia MIT; se conserva la atribución original en `LICENSE`.

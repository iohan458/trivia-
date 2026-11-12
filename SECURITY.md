[SECURITY.md](https://github.com/user-attachments/files/34723631/SECURITY.md)
# SECURITY.md – Grupo 8 (Maidana – Melnik) · Trivia

> Proyecto Integrador Final – ExpoTécnica 2026 · E.P.E.T. Nº1 UNESCO
> Este documento identifica los activos, las amenazas y las medidas de seguridad de la aplicación de Trivia, y se relaciona con `REDES.md` (la tabla de integración usa los mismos IDs de amenaza).
>
> Los textos marcados con `TODO` o con estado **Pendiente** son cosas que tienen que verificar o implementar ustedes antes de la entrega.

---

## 1. Alcance y activos a proteger

| Activo | Descripción | Por qué importa |
|---|---|---|
| Aplicación web | Flask (Python) + HTML/CSS/JS, en el servidor de aplicación (`192.168.8.98`) | Es el punto de entrada de todos los jugadores |
| Base de datos | MongoDB en `192.168.8.114`, colecciones `preguntas` y `puntuaciones` | Contiene las respuestas correctas y el ranking |
| Respuestas correctas | Se guardan solo en el servidor; el navegador recibe enunciado y opciones | Si se filtran, el juego pierde sentido |
| Ranking / puntuaciones | Nombre, puntaje, categoría y fecha | Integridad: que nadie pueda falsificarlo |
| Equipos de red | Router y switch | Su compromiso rompe todas las demás medidas |
| Código y repositorio | GitHub | Puede contener claves por error |

**Datos personales:** la app solo guarda un nombre o apodo de hasta 25 caracteres. No pide correo, DNI ni contraseña, lo que reduce mucho el riesgo.

---

## 2. Amenazas identificadas

| ID | Amenaza | Impacto | Probabilidad |
|---|---|---|---|
| T1 | Acceso no autorizado a los servidores desde la red de invitados | Alto | Media |
| T2 | Acceso directo a MongoDB (27017) desde PCs de usuarios o invitados | Alto | Media |
| T3 | Escaneo de puertos y movimiento lateral desde una PC comprometida | Medio | Media |
| T4 | Acceso no autorizado a la administración de router y switch (credenciales débiles, Telnet) | Alto | Media |
| T5 | Conexión de equipos no autorizados a la red cableada o Wi-Fi | Medio | Media |
| T6 | Falsificación de la sesión de Flask si se conoce la clave secreta | Alto | Baja (si se cambia la clave) |
| T7 | Trampa en el juego: reutilizar una cookie de sesión vieja para volver a responder | Medio | Media |
| T8 | Inyección de código en nombres de jugador (XSS) mostrados en el ranking | Medio | Media |
| T9 | Inyección NoSQL mediante datos enviados al servidor | Alto | Baja |
| T10 | Spam al ranking y abuso de la API (partidas ilimitadas, nombres falsos) | Medio | Alta |
| T11 | Interceptación del tráfico (sniffing) en la red local, sin cifrado | Medio | Baja |
| T12 | Exposición de información por modo debug o mensajes de error | Alto | Baja |
| T13 | Pérdida o corrupción de la base de datos | Medio | Baja |
| T14 | Filtración de claves en el repositorio de GitHub | Alto | Media |

---

## 3. Medidas por capa

### 3.1 Red (detalle en `REDES.md`)

| Medida | Mitiga | Estado |
|---|---|---|
| Segmentación en VLANs 10, 20, 30, 40 y 99 | T1, T2, T3 | Implementada en Packet Tracer |
| ACL `INVITADOS_IN`: invitados sin acceso a servidores, BD, administración ni usuarios | T1 | Implementada |
| ACL `USUARIOS_IN`: usuarios solo llegan a la app por DNS, HTTP y ping | T3 | Implementada |
| ACL `BD_OUT`: a la VLAN de BD solo entra el servidor de aplicación por 27017 | T2 | Implementada |
| SSH v2, sin Telnet, `enable secret`, `service password-encryption`, banner | T4 | Implementada |
| VLAN 99 de administración | T4 | Implementada |
| Port Security en los puertos de PCs | T5 | Implementada (opcional) |
| WPA2 en el Wi-Fi de invitados | T5 | Implementada (opcional) |
| Puertos sin uso apagados (`shutdown`) | T5 | Implementada |

### 3.2 Aplicación (código de `app.py`)

| Medida | Mitiga | Estado |
|---|---|---|
| Las respuestas correctas nunca viajan al navegador: `Pregunta.para_mostrar()` solo envía enunciado y opciones, y la corrección se hace en el servidor | Trampa en el juego | Implementada |
| El nombre se recorta a 25 caracteres y se convierte a texto (`str(...)[:25]`) | T9, T10 | Implementada |
| La categoría se valida contra una lista fija; la respuesta debe ser texto y una letra válida (A–D) | T9 | Implementada |
| Los filtros de MongoDB usan siempre valores ya convertidos a texto o `ObjectId` de la sesión, nunca objetos del usuario | T9 | Implementada |
| Mensajes de error genéricos, sin detalles internos ni trazas | T12 | Implementada |
| Modo debug apagado por defecto (`FLASK_DEBUG=false`) | T12 | Implementada |
| La clave de sesión se lee de la variable de entorno `FLASK_SECRET_KEY` | T6, T14 | Implementada, pero el valor por defecto es de desarrollo |
| Cookies de sesión: `SESSION_COOKIE_HTTPONLY=True` (valor por defecto de Flask) y `SESSION_COOKIE_SAMESITE="Lax"` | T6, T7 | **Pendiente** de agregar `SameSite` |
| Mostrar nombres en el ranking con `textContent` (no `innerHTML`) en el JavaScript | T8 | **Pendiente: TODO verificar en `static/*.js`** |
| Límite de partidas por IP (rate limiting) | T10 | **Pendiente** (ver 3.4) |

### 3.3 Base de datos y servidores

| Medida | Mitiga | Estado |
|---|---|---|
| Autenticación activada en MongoDB (`security.authorization: enabled`) con un usuario solo para la app, con permisos `readWrite` sobre `trivia_db` | T2 | **Pendiente** |
| `bindIp: 192.168.8.114` en `mongod.conf` | T2 | **Pendiente** |
| `MONGODB_URI` con usuario y clave por variable de entorno | T2, T14 | **Pendiente** |
| Firewall del host: `ufw allow from 192.168.8.98 to any port 27017` y `ufw default deny incoming` | T2 | **Pendiente** |
| Copias de seguridad periódicas con `mongodump` | T13 | **Pendiente** |
| Actualizaciones del sistema operativo y de las dependencias (`pip list --outdated`) | T12 | **Pendiente** |
| `.env` en `.gitignore`; ninguna clave en el código ni en `REDES.md` | T14 | **TODO verificar** |

### 3.4 Mejoras recomendadas (si les da el tiempo)

- **HTTPS con nginx** (certificado autofirmado) y abrir el puerto 443 en la ACL. Mitiga T11.
- **Rate limiting** en nginx (`limit_req_zone`) o con la librería Flask-Limiter en `/api/quiz/iniciar` y `/api/quiz/responder`. Mitiga T10.
- **Estado de la partida en el servidor:** hoy `pregunta_ids` y `respuestas_usuario` viven en la cookie de sesión, que está firmada pero no cifrada. Quien la copie antes de responder puede volver a usarla para probar respuestas (T7). Guardar la partida en MongoDB, con un identificador aleatorio en la cookie, lo evita.
- **Registro de eventos (logs):** guardar intentos fallidos de SSH en el router (`logging buffered`) y errores de la app.

---

## 4. Riesgos que quedan (riesgo residual)

| Riesgo | Por qué se acepta |
|---|---|
| El ranking solo guarda un nombre sin verificar quién es el jugador | La app es educativa y no maneja datos sensibles; cualquiera puede escribir cualquier apodo |
| Tráfico HTTP sin cifrar dentro de la red local (si no se hace la mejora de HTTPS) | La red es interna, segmentada, y la app no transmite claves ni datos personales |
| Simulación en Packet Tracer: la ACL de MongoDB se prueba con un paquete de prueba, no con MongoDB real | Es una limitación de la herramienta; en un despliegue real se verifica con `mongosh` |

---

## 5. Respuesta ante incidentes (resumen)

1. **Detectar:** contadores de `show access-lists`, logs del router, comportamiento raro en el ranking.
2. **Contener:** apagar la boca del switch del equipo sospechoso (`shutdown`) o sacar al invitado de la VLAN 30.
3. **Corregir:** cambiar claves (`FLASK_SECRET_KEY`, usuario de MongoDB, enable secret), actualizar el sistema, restaurar el ranking desde la copia de seguridad.
4. **Registrar:** anotar lo ocurrido y la solución en la bitácora de `REDES.md` y en el tablero de Trello.

---

## 6. Verificación

| Medida | Cómo se prueba | Resultado |
|---|---|---|
| ACL de invitados | Ping de la laptop de invitados a `192.168.8.98` | TODO |
| ACL de MongoDB | Paquete TCP 27017 desde Usuarios (bloqueado) y desde SRV-APP (permitido) | TODO |
| SSH sin Telnet | `ssh` entra y `telnet` es rechazado | TODO |
| Validación de entradas | Enviar una categoría inexistente, un nombre vacío y una respuesta `Z` a la API: devuelve error 400 | TODO |
| Respuestas en el servidor | En el navegador (F12 → Network), la respuesta de `/api/quiz/iniciar` no contiene `respuesta_correcta` | TODO |
| Contraseñas cifradas | `show running-config` no muestra claves legibles | TODO |

---

## 7. Roles y responsabilidades

| Integrante | Responsabilidad |
|---|---|
| Maidana | TODO (por ejemplo: seguridad de la aplicación y la base de datos) |
| Melnik | TODO (por ejemplo: seguridad de red y documentación) |

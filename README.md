# Trivia

Juego educativo de 10 preguntas hecho con Python, Flask, MongoDB, HTML, CSS y JavaScript. Después de ingresar el nombre, cada jugador elige una categoría: Ciencia, Deportes, Arte, Historia, Geografía o Matemática. Cada partida usa exclusivamente preguntas de la categoría seleccionada.

## La página

La página principal guía al jugador durante toda la partida, sin necesidad de crear una cuenta:

1. **Ingreso del nombre:** se solicita un nombre de hasta 25 caracteres.
2. **Selección de categoría:** se muestran las seis categorías disponibles con una breve descripción.
3. **Partida:** aparecen diez preguntas elegidas al azar, cada una con cuatro opciones. La página indica la categoría, el número de pregunta, el progreso y el puntaje acumulado.
4. **Resultado:** al finalizar se muestra el puntaje sobre 1000 y la mejor puntuación registrada para ese nombre y categoría. Desde aquí se puede iniciar otra partida o consultar el ranking.

Cada acierto suma 100 puntos. Después de responder, se indica si la opción fue correcta y se revela la respuesta correcta antes de continuar. Las preguntas y respuestas se validan en el servidor.

El ranking muestra hasta diez resultados, ordenados por puntuación y, en caso de empate, por fecha. Se puede consultar el ranking de la categoría jugada; durante una partida se excluyen de la lista los resultados con el mismo nombre del jugador. La interfaz se adapta a pantallas pequeñas y ofrece estados y controles accesibles para navegar el juego.

## Requisitos

- Python 3.10 o superior.
- Docker Compose, o una instalación local de MongoDB.

## Ejecutar en Linux

1. Crear y activar un entorno virtual:

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	```

2. Instalar las dependencias:

	```bash
	pip install -r requirements.txt
	```

3. Iniciar MongoDB local con Docker:

	```bash
	docker compose up -d mongodb
	```

4. Iniciar la aplicación:

	```bash
	python app.py
	```

5. Abrir <http://127.0.0.1:5000>.

La aplicación carga 20 preguntas de ejemplo por categoría (120 en total) y completa las categorías de una base de datos existente. Cada partida selecciona al azar 10 preguntas de la categoría elegida, sin repetirlas en la misma partida. Cada respuesta correcta suma 100 puntos. Al terminar, el resultado se guarda y aparece en el ranking de esa categoría.

## Clases POO

- `Pregunta`: contiene categoría, texto, opciones y respuesta correcta; solo publica el texto y las opciones durante el juego.
- `Quiz`: controla las preguntas, las respuestas seleccionadas, el avance y la puntuación.
- `Puntuacion`: representa un resultado y lo prepara para guardar o mostrar.
- `RepositorioQuiz`: consulta y guarda datos en MongoDB.

## Base de datos

La aplicación usa la base `trivia_db` y exactamente dos colecciones:

- `preguntas`: texto, opciones, respuesta correcta y orden de las preguntas.
- `puntuaciones`: nombre, categoría, puntuación, máximo y fecha.

Configuración opcional mediante variables de entorno:

- `MONGODB_URI`: dirección de MongoDB (por defecto `mongodb://localhost:27017`).
- `MONGODB_DATABASE`: nombre de la base (por defecto `trivia_db`).
- `FLASK_SECRET_KEY`: clave para firmar las sesiones; cambiá el valor de desarrollo antes de publicar la aplicación.
- `FLASK_DEBUG=true`: activa el modo de depuración local.

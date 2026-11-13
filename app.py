# Este archivo contiene las reglas del juego y las rutas que conectan la página
# con la base de datos. El navegador muestra las preguntas; el servidor guarda
# las respuestas correctas y calcula los resultados.
import html
import os
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from flask import Flask, jsonify, render_template, request, session
from pymongo import MongoClient
from pymongo.errors import PyMongoError


# Información que la página necesita para mostrar las categorías disponibles.
CATEGORIAS = [
    {"id": "ciencia", "nombre": "Ciencia", "icono": "⚗", "descripcion": "Naturaleza, química y espacio"},
    {"id": "deportes", "nombre": "Deportes", "icono": "⚽", "descripcion": "Reglas, juegos y competencias"},
    {"id": "arte", "nombre": "Arte", "icono": "🎨", "descripcion": "Pintura, música y literatura"},
    {"id": "historia", "nombre": "Historia", "icono": "🏛", "descripcion": "Personajes y hechos del pasado"},
    {"id": "geografia", "nombre": "Geografía", "icono": "🌎", "descripcion": "Países, lugares y mapas"},
    {"id": "matematica", "nombre": "Matemática", "icono": "📐", "descripcion": "Números, formas y lógica"},
]


def sanitizar_nombre(valor):
    if not isinstance(valor, str):
        return ""
    texto = "".join(caracter for caracter in valor if caracter.isprintable()).strip()
    return html.escape(texto[:25], quote=True)




# Representa una pregunta mientras se juega y prepara su versión pública.
class Pregunta:
    def __init__(self, identificador, texto, opciones, respuesta_correcta, categoria):
        self.identificador = str(identificador)
        self.texto = texto
        self.opciones = opciones
        self.respuesta_correcta = respuesta_correcta.upper()
        self.categoria = categoria

    @classmethod
    def desde_documento(cls, documento):
        return cls(
            documento["_id"],
            documento["texto"],
            documento["opciones"],
            documento["respuesta_correcta"],
            documento["categoria"],
        )

    def para_mostrar(self):
        # La respuesta correcta se queda en el servidor: el jugador solo recibe
        # el enunciado y las opciones.
        return {
            "texto": self.texto,
            "opciones": self.opciones,
            "categoria": self.categoria,
        }


# Lleva el avance y los puntos de una partida en memoria.
class Quiz:
    PUNTOS_POR_RESPUESTA = 100

    def __init__(self, preguntas, respuestas_usuario=None):
        self.preguntas = preguntas
        self.respuestas_usuario = list(respuestas_usuario or [])
        self.puntuacion = sum(
            self.PUNTOS_POR_RESPUESTA
            for pregunta, respuesta in zip(self.preguntas, self.respuestas_usuario)
            if respuesta == pregunta.respuesta_correcta
        )

    @property
    def terminado(self):
        return len(self.respuestas_usuario) >= len(self.preguntas)

    @property
    def pregunta_actual(self):
        # La posición de la pregunta depende de cuántas respuestas ya se dieron.
        if self.terminado:
            return None
        return self.preguntas[len(self.respuestas_usuario)]

    def responder(self, letra):
        if self.terminado:
            raise ValueError("El juego ya terminó.")

        respuesta = letra.strip().upper()
        pregunta = self.pregunta_actual
        letras_validas = {opcion["letra"] for opcion in pregunta.opciones}
        if respuesta not in letras_validas:
            raise ValueError("Seleccioná una de las opciones disponibles.")

        es_correcta = respuesta == pregunta.respuesta_correcta
        self.respuestas_usuario.append(respuesta)
        if es_correcta:
            self.puntuacion += self.PUNTOS_POR_RESPUESTA

        return {
            "correcta": es_correcta,
            "respuesta_correcta": pregunta.respuesta_correcta,
            "puntuacion": self.puntuacion,
            "terminado": self.terminado,
        }


# Agrupa el resultado de una persona y lo prepara para guardarlo o mostrarlo.
class Puntuacion:
    def __init__(self, nombre, puntuacion, total=1000, fecha=None, categoria=None):
        self.nombre = nombre
        self.nombre_normalizado = nombre.casefold()
        self.puntuacion = puntuacion
        self.total = total
        self.fecha = fecha or datetime.now(timezone.utc)
        self.categoria = categoria

    @classmethod
    def desde_documento(cls, documento):
        return cls(
            documento["nombre"],
            documento["puntuacion"],
            documento.get("total", 1000),
            documento.get("fecha"),
            documento.get("categoria"),
        )

    def a_documento(self):
        documento = {
            "nombre": self.nombre,
            "nombre_normalizado": self.nombre_normalizado,
            "puntuacion": self.puntuacion,
            "total": self.total,
            "fecha": self.fecha,
        }
        if self.categoria:
            documento["categoria"] = self.categoria
        return documento

    def para_mostrar(self, puesto=None):
        resultado = {
            "nombre": html.unescape(self.nombre),
            "puntuacion": self.puntuacion,
            "total": self.total,
        }
        if self.categoria:
            resultado["categoria"] = self.categoria
        if puesto is not None:
            resultado["puesto"] = puesto
        return resultado


# Reúne las operaciones que leen y escriben preguntas y puntuaciones en MongoDB.
class RepositorioQuiz:
    def __init__(self, base_datos):
        self.coleccion_preguntas = base_datos["preguntas"]
        self.coleccion_puntuaciones = base_datos["puntuaciones"]

    def obtener_preguntas_para_quiz(self, categoria):
        # MongoDB elige al azar diez preguntas de la categoría seleccionada.
        # Las preguntas se cargan una sola vez con seed.py.
        documentos = list(
            self.coleccion_preguntas.aggregate(
                [
                    {"$match": {"categoria": categoria}},
                    {"$sample": {"size": 10}},
                ]
            )
        )

        if len(documentos) < 10:
            raise ValueError("Esta categoría necesita al menos 10 preguntas.")
        return [Pregunta.desde_documento(doc) for doc in documentos[:10]]

    def obtener_preguntas_por_ids(self, identificadores):
        # Recupera las mismas preguntas de la partida para revisar las respuestas.
        ids = [ObjectId(identificador) for identificador in identificadores]
        documentos = self.coleccion_preguntas.find({"_id": {"$in": ids}})
        por_id = {str(documento["_id"]): documento for documento in documentos}
        if len(por_id) != len(ids):
            raise ValueError("No se pudieron recuperar las preguntas del juego.")
        return [Pregunta.desde_documento(por_id[identificador]) for identificador in identificadores]

    def guardar_puntuacion(self, puntuacion):
        self.coleccion_puntuaciones.insert_one(puntuacion.a_documento())

    def obtener_top10(self, categoria=None, excluir_nombre=None):
        # Ordena primero los puntajes más altos y limita la lista a diez personas.
        filtro = {"categoria": categoria} if categoria else {}
        if excluir_nombre:
            filtro["nombre_normalizado"] = {"$ne": excluir_nombre.casefold()}
        documentos = self.coleccion_puntuaciones.find(filtro).sort(
            [("puntuacion", -1), ("fecha", 1)]
        ).limit(10)
        return [
            Puntuacion.desde_documento(documento).para_mostrar(puesto)
            for puesto, documento in enumerate(documentos, start=1)
        ]

    def obtener_mejor_puntuacion(self, nombre, categoria=None):
        filtro = {"nombre_normalizado": nombre.casefold()}
        if categoria:
            filtro["categoria"] = categoria
        documento = self.coleccion_puntuaciones.find_one(
            filtro,
            sort=[("puntuacion", -1), ("fecha", 1)],
        )
        if documento is None:
            return None
        return Puntuacion.desde_documento(documento).para_mostrar()


def create_app(repository=None):
    # Prepara Flask y conecta la aplicación con MongoDB.
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
    if not os.getenv("FLASK_SECRET_KEY"):
        app.logger.warning(
            "FLASK_SECRET_KEY no está configurada; las sesiones se invalidarán "
            "cuando se reinicie la aplicación."
        )

    if repository is None:
        cliente = MongoClient(
            os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2500,
        )
        base_datos = cliente[os.getenv("MONGODB_DATABASE", "trivia_db")]
        repository = RepositorioQuiz(base_datos)

    app.config["REPOSITORIO_QUIZ"] = repository

    @app.errorhandler(500)
    def error_interno(error):
        excepcion = error.original_exception or error
        app.logger.error(
            "Error interno al procesar la solicitud.",
            exc_info=(type(excepcion), excepcion, excepcion.__traceback__),
        )
        return jsonify({"error": "Ocurrió un error interno. Intentá nuevamente más tarde."}), 500

    @app.get("/")
    def inicio():
        # Entrega la página principal del juego.
        return render_template("index.html")

    @app.get("/api/categorias")
    def categorias():
        # Envía al navegador la lista de categorías para que pueda mostrarlas.
        return jsonify(CATEGORIAS)

    @app.post("/api/quiz/iniciar")
    def iniciar_quiz():
        # Comprueba el nombre y la categoría, elige preguntas y recuerda la
        # partida en la sesión del navegador.
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Los datos enviados no son válidos."}), 400

        nombre = sanitizar_nombre(datos.get("nombre"))
        categoria = datos.get("categoria")
        if not nombre:
            return jsonify({"error": "Ingresá tu nombre para empezar."}), 400
        if not isinstance(categoria, str) or categoria not in {
            item["id"] for item in CATEGORIAS
        }:
            return jsonify({"error": "Elegí una categoría disponible."}), 400

        try:
            preguntas = repository.obtener_preguntas_para_quiz(categoria)
        except ValueError as error:
            return jsonify({"error": str(error)}), 503
        except PyMongoError:
            app.logger.exception("No se pudieron obtener preguntas de MongoDB.")
            return jsonify({"error": "No se pudo conectar con MongoDB."}), 503

        quiz = Quiz(preguntas)
        session.clear()
        session["jugador"] = nombre
        session["categoria"] = categoria
        session["pregunta_ids"] = [pregunta.identificador for pregunta in preguntas]
        session["respuestas_usuario"] = quiz.respuestas_usuario

        return jsonify(
            {
                "jugador": html.unescape(nombre),
                "categoria": categoria,
                "categoria_nombre": next(
                    item["nombre"] for item in CATEGORIAS if item["id"] == categoria
                ),
                "numero_pregunta": 1,
                "total_preguntas": len(preguntas),
                "puntuacion": quiz.puntuacion,
                "pregunta": quiz.pregunta_actual.para_mostrar(),
            }
        )

    @app.post("/api/quiz/responder")
    def responder():
        # Revisa una respuesta y devuelve los puntos y el siguiente paso del juego.
        if "pregunta_ids" not in session or "jugador" not in session:
            return jsonify({"error": "Iniciá una partida antes de responder."}), 400

        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Los datos enviados no son válidos."}), 400
        letra = datos.get("respuesta", "")
        if not isinstance(letra, str):
            return jsonify({"error": "La respuesta debe ser una opción válida."}), 400

        try:
            preguntas = repository.obtener_preguntas_por_ids(session["pregunta_ids"])
            quiz = Quiz(preguntas, session.get("respuestas_usuario", []))
            resultado = quiz.responder(letra)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except PyMongoError:
            app.logger.exception("No se pudieron recuperar preguntas de MongoDB.")
            return jsonify({"error": "No se pudo conectar con MongoDB."}), 503

        session["respuestas_usuario"] = quiz.respuestas_usuario
        respuesta = {
            **resultado,
            "numero_pregunta": len(quiz.respuestas_usuario),
            "total_preguntas": len(quiz.preguntas),
        }

        if quiz.terminado:
            puntuacion = Puntuacion(
                session["jugador"], quiz.puntuacion, categoria=session["categoria"]
            )
            try:
                repository.guardar_puntuacion(puntuacion)
                respuesta["mejor_puntuacion"] = repository.obtener_mejor_puntuacion(
                    session["jugador"], session["categoria"]
                )
                respuesta["top10"] = repository.obtener_top10(session["categoria"])
            except PyMongoError:
                app.logger.exception("No se pudo guardar o consultar el resultado en MongoDB.")
                return jsonify({"error": "No se pudo guardar el resultado en MongoDB."}), 503
            session["partida_finalizada"] = True
            respuesta["jugador"] = html.unescape(session["jugador"])
        else:
            respuesta["siguiente_pregunta"] = quiz.pregunta_actual.para_mostrar()

        return jsonify(respuesta)

    @app.get("/api/ranking")
    def ranking():
        # Devuelve los mejores puntajes cuando el jugador pide ver el ranking.
        nombre = sanitizar_nombre(request.args.get("nombre", ""))
        categoria = request.args.get("categoria")
        excluir_nombre = sanitizar_nombre(request.args.get("excluir", ""))
        if categoria and categoria not in {item["id"] for item in CATEGORIAS}:
            return jsonify({"error": "La categoría no existe."}), 400
        try:
            top10 = repository.obtener_top10(categoria, excluir_nombre)
            mejor = (
                repository.obtener_mejor_puntuacion(nombre, categoria)
                if nombre
                else None
            )
        except PyMongoError:
            app.logger.exception("No se pudo consultar el ranking en MongoDB.")
            return jsonify({"error": "No se pudo conectar con MongoDB."}), 503
        return jsonify({"top10": top10, "mejor_puntuacion": mejor})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

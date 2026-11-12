# Este archivo contiene las reglas del juego y las rutas que conectan la página
# con la base de datos. El navegador muestra las preguntas; el servidor guarda
# las respuestas correctas y calcula los resultados.
import html
import os
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from flask import Flask, jsonify, render_template, request, session
from pymongo import MongoClient, UpdateOne
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


# Banco de preguntas de ejemplo. Cada fila tiene el enunciado, las cuatro
# opciones y la letra de la opción correcta.
BANCO_PREGUNTAS = {
    "ciencia": [
        ("¿Cuál es el símbolo químico del hierro?", ["Fe", "H", "F", "He"], "A"),
        ("¿Qué planeta es conocido como el planeta rojo?", ["Venus", "Marte", "Júpiter", "Mercurio"], "B"),
        ("¿Qué gas absorben principalmente las plantas?", ["Oxígeno", "Nitrógeno", "Hidrógeno", "Dióxido de carbono"], "D"),
        ("¿Cuál es la fórmula química del agua?", ["CO₂", "NaCl", "O₂", "H₂O"], "D"),
        ("¿En qué unidad se mide la fuerza?", ["Joule", "Newton", "Watt", "Pascal"], "B"),
        ("¿Cuál es la estrella más cercana a la Tierra?", ["Sirio", "Próxima Centauri", "El Sol", "Vega"], "C"),
        ("¿Qué molécula contiene gran parte de la información hereditaria?", ["ADN", "Glucosa", "Agua", "Oxígeno"], "A"),
        ("¿A qué temperatura hierve el agua al nivel del mar?", ["50 °C", "80 °C", "100 °C", "120 °C"], "C"),
        ("¿Qué órgano usamos principalmente para respirar?", ["Estómago", "Pulmones", "Riñones", "Páncreas"], "B"),
        ("¿Cómo se llama el centro de un átomo?", ["Molécula", "Corteza", "Núcleo", "Célula"], "C"),
        ("¿Qué proceso permite a las plantas transformar luz en energía química?", ["Fermentación", "Fotosíntesis", "Respiración celular", "Evaporación"], "B"),
        ("¿Qué partícula subatómica tiene carga eléctrica negativa?", ["Protón", "Neutrón", "Electrón", "Núcleo"], "C"),
        ("¿Qué elemento químico es líquido a temperatura ambiente?", ["Mercurio", "Aluminio", "Cobre", "Silicio"], "A"),
        ("¿Qué escala se usa para medir la acidez o alcalinidad de una solución?", ["Richter", "Beaufort", "pH", "Kelvin"], "C"),
        ("¿Cuál es la unidad del Sistema Internacional para medir energía?", ["Newton", "Joule", "Pascal", "Amperio"], "B"),
        ("¿Qué estructura celular contiene la mayor parte del ADN en una célula animal?", ["Membrana", "Núcleo", "Ribosoma", "Citoplasma"], "B"),
        ("¿Cómo se llama el cambio de estado de gas a líquido?", ["Fusión", "Sublimación", "Condensación", "Solidificación"], "C"),
        ("¿Qué tipo de enlace se forma al compartir electrones entre átomos?", ["Iónico", "Covalente", "Metálico", "Magnético"], "B"),
        ("¿Qué planeta del sistema solar tiene el período orbital más corto?", ["Venus", "Mercurio", "Marte", "Neptuno"], "B"),
        ("¿Qué vasos sanguíneos llevan la sangre desde el corazón hacia el cuerpo?", ["Venas", "Arterias", "Capilares", "Alvéolos"], "B"),
    ],
    "deportes": [
        ("¿Cuántos jugadores de un equipo de fútbol hay en la cancha al comenzar?", ["9", "10", "11", "12"], "C"),
        ("¿Cuántos puntos vale un tiro libre en básquet?", ["1", "2", "3", "4"], "A"),
        ("¿Cuántos torneos de Grand Slam de tenis hay por año?", ["2", "3", "4", "5"], "C"),
        ("¿Cuántos jugadores por equipo hay en cancha en vóley?", ["5", "6", "7", "8"], "B"),
        ("¿Qué distancia oficial tiene una maratón?", ["21,097 km", "40 km", "42,195 km", "50 km"], "C"),
        ("¿Desde qué distancia se ejecuta un penal en fútbol?", ["9 metros", "10 metros", "11 metros", "12 metros"], "C"),
        ("¿Cuántos jugadores por equipo hay en cancha en handball?", ["5", "6", "7", "8"], "C"),
        ("¿En qué deporte se disputa el torneo de Wimbledon?", ["Golf", "Tenis", "Críquet", "Rugby"], "B"),
        ("¿Cada cuántos años se celebran los Juegos Olímpicos de verano?", ["2 años", "3 años", "4 años", "5 años"], "C"),
        ("¿Qué parte del cuerpo no puede usar un jugador de campo para tocar la pelota en fútbol?", ["Cabeza", "Pecho", "Pie", "Mano"], "D"),
        ("¿Cuántos puntos vale un lanzamiento convertido desde fuera del arco en básquet?", ["1", "2", "3", "4"], "C"),
        ("¿Cuántos eventos individuales incluye el decatlón masculino?", ["8", "9", "10", "12"], "C"),
        ("¿Qué distancia mide una vuelta completa a una pista olímpica de atletismo?", ["200 m", "300 m", "400 m", "800 m"], "C"),
        ("En tenis, ¿qué término indica que un jugador no anotó puntos en un game?", ["Love", "Deuce", "Let", "Break"], "A"),
        ("¿Cuántos jugadores por equipo están en cancha en un partido de rugby union?", ["13", "14", "15", "16"], "C"),
        ("¿Cuánto dura cada tiempo de un partido adulto de handball, sin contar el descanso?", ["20 minutos", "25 minutos", "30 minutos", "45 minutos"], "C"),
        ("En vóley, ¿a cuántos puntos se juega normalmente un set que no es el desempate?", ["15", "21", "25", "30"], "C"),
        ("¿Cuándo se sanciona normalmente una posición adelantada en fútbol?", ["Al recibir un saque de banda", "Si está adelantado cuando un compañero juega el balón y participa", "Al estar dentro del área", "Cada vez que supera al arquero"], "B"),
        ("¿Qué prueba de natación combina mariposa, espalda, pecho y libre?", ["Relevo", "Estilo combinado", "Nado sincronizado", "Aguas abiertas"], "B"),
        ("¿Qué acción permite recuperar el balón tras un lanzamiento fallido en básquet?", ["Bloqueo", "Rebote", "Saque", "Pase de pecho"], "B"),
    ],
    "arte": [
        ("¿Quién escribió Don Quijote de la Mancha?", ["Miguel de Cervantes", "Federico García Lorca", "Lope de Vega", "Francisco de Quevedo"], "A"),
        ("¿Quién pintó la Mona Lisa?", ["Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso", "Claude Monet"], "B"),
        ("¿Quién pintó La noche estrellada?", ["Salvador Dalí", "Claude Monet", "Vincent van Gogh", "Rembrandt"], "C"),
        ("¿Cuántas teclas tiene aproximadamente un piano estándar?", ["66", "76", "88", "100"], "C"),
        ("¿Qué caracteriza principalmente a una escultura?", ["Tiene volumen y tres dimensiones", "Está escrita en versos", "Solo usa sonidos", "Se proyecta en una pantalla"], "A"),
        ("¿Quién pintó el Guernica?", ["Pablo Picasso", "Joan Miró", "Diego Velázquez", "Francisco de Goya"], "A"),
        ("¿Cuántas líneas tiene un pentagrama musical?", ["4", "5", "6", "7"], "B"),
        ("¿Qué baile es tradicional de Argentina?", ["Samba", "Tango", "Flamenco", "Vals vienés"], "B"),
        ("¿Quién compuso Las cuatro estaciones?", ["Mozart", "Beethoven", "Antonio Vivaldi", "Chopin"], "C"),
        ("¿En qué ciudad está el museo del Louvre?", ["Roma", "Madrid", "París", "Atenas"], "C"),
        ("¿Cuántos versos tiene un soneto clásico en español?", ["12", "14", "16", "18"], "B"),
        ("¿Qué técnica mural aplica pigmentos sobre yeso todavía húmedo?", ["Temple", "Fresco", "Grabado", "Mosaico"], "B"),
        ("¿Qué pintor es una figura central del impresionismo y realizó varias series de nenúfares?", ["Claude Monet", "Paul Cézanne", "Edgar Degas", "Henri Matisse"], "A"),
        ("¿Cómo se llama el texto que contiene las palabras de una ópera?", ["Libreto", "Partitura", "Soneto", "Crónica"], "A"),
        ("¿Qué recurso visual crea volumen mediante el contraste marcado entre luz y sombra?", ["Perspectiva aérea", "Claroscuro", "Puntillismo", "Collage"], "B"),
        ("¿Qué arquitecto diseñó la basílica de la Sagrada Familia de Barcelona?", ["Antoni Gaudí", "Le Corbusier", "Frank Lloyd Wright", "Oscar Niemeyer"], "A"),
        ("¿Qué dos artistas son considerados iniciadores del cubismo?", ["Dalí y Miró", "Picasso y Braque", "Monet y Renoir", "Kahlo y Rivera"], "B"),
        ("¿Qué compás suele asociarse con el vals tradicional?", ["2/4", "3/4", "4/4", "6/8"], "B"),
        ("¿Qué figura retórica establece una comparación implícita entre dos elementos?", ["Hipérbole", "Metáfora", "Anáfora", "Ironía"], "B"),
        ("¿Qué escultor italiano realizó el David de mármol que se conserva en Florencia?", ["Donatello", "Miguel Ángel", "Bernini", "Canova"], "B"),
    ],
    "historia": [
        ("¿En qué año declaró su independencia Argentina?", ["1810", "1816", "1820", "1853"], "B"),
        ("¿En qué año comenzó la Revolución francesa?", ["1776", "1789", "1812", "1848"], "B"),
        ("¿En qué año cayó el Muro de Berlín?", ["1961", "1975", "1989", "1995"], "C"),
        ("¿Quién fue el primer ser humano en pisar la Luna?", ["Yuri Gagarin", "Neil Armstrong", "Buzz Aldrin", "John Glenn"], "B"),
        ("¿En qué año terminó la Segunda Guerra Mundial?", ["1939", "1942", "1945", "1950"], "C"),
        ("¿Qué ciudad fue el centro del Imperio romano?", ["Atenas", "Roma", "Cartago", "Alejandría"], "B"),
        ("¿Quién fue el primer presidente de Argentina?", ["Domingo Faustino Sarmiento", "Bernardino Rivadavia", "Bartolomé Mitre", "Justo José de Urquiza"], "B"),
        ("¿Quiénes construyeron las pirámides de Guiza?", ["Los antiguos egipcios", "Los romanos", "Los fenicios", "Los persas"], "A"),
        ("¿En qué año llegó Cristóbal Colón a América?", ["1342", "1492", "1510", "1600"], "B"),
        ("¿En qué año se firmó la Declaración de Independencia de Estados Unidos?", ["1492", "1648", "1776", "1816"], "C"),
        ("¿Qué tratado de 1919 estableció las condiciones de paz para Alemania tras la Primera Guerra Mundial?", ["Tratado de Utrecht", "Tratado de Versalles", "Tratado de Tordesillas", "Tratado de París"], "B"),
        ("¿En qué año comenzó la Restauración Meiji en Japón?", ["1603", "1756", "1868", "1912"], "C"),
        ("¿Qué documento de 1215 limitó algunos poderes del rey Juan de Inglaterra?", ["La Carta Magna", "El Edicto de Milán", "La Bula de Oro", "El Acta de Navegación"], "A"),
        ("¿Qué ciudad fue la capital del Imperio bizantino durante la mayor parte de su historia?", ["Atenas", "Constantinopla", "Alejandría", "Antioquía"], "B"),
        ("¿En qué año se declaró la independencia de Haití?", ["1776", "1791", "1804", "1816"], "C"),
        ("¿Qué civilización construyó la ciudad de Machu Picchu?", ["Maya", "Azteca", "Inca", "Moche"], "C"),
        ("¿En qué país comenzó la Revolución Industrial del siglo XVIII?", ["Francia", "Gran Bretaña", "Alemania", "Estados Unidos"], "B"),
        ("¿En qué año ocurrió la crisis de los misiles de Cuba?", ["1956", "1961", "1962", "1968"], "C"),
        ("¿Qué tratado de 1494 dividió áreas de exploración entre Castilla y Portugal?", ["Tratado de Versalles", "Tratado de Tordesillas", "Tratado de Utrecht", "Tratado de Alcáçovas"], "B"),
        ("¿En qué ciudad se celebró la conferencia europea de 1884-1885 sobre la ocupación colonial de África?", ["Berlín", "París", "Londres", "Viena"], "A"),
    ],
    "geografia": [
        ("¿Cuál es la capital de Argentina?", ["Buenos Aires", "Mendoza", "La Plata", "Córdoba"], "A"),
        ("¿Cuál es el océano más grande del planeta?", ["Atlántico", "Índico", "Pacífico", "Ártico"], "C"),
        ("¿En qué continente se encuentra Egipto?", ["Asia", "África", "Europa", "Oceanía"], "B"),
        ("¿En qué cordillera se encuentra el Aconcagua?", ["Los Alpes", "Los Andes", "El Himalaya", "Los Pirineos"], "B"),
        ("¿Cuál es la capital de Japón?", ["Kioto", "Osaka", "Tokio", "Hiroshima"], "C"),
        ("¿Cuál es la capital de Francia?", ["Lyon", "Marsella", "París", "Niza"], "C"),
        ("¿En qué continente se encuentra el desierto del Sahara?", ["Asia", "África", "América", "Europa"], "B"),
        ("¿Qué línea imaginaria divide la Tierra en hemisferios norte y sur?", ["Meridiano de Greenwich", "Trópico de Cáncer", "Ecuador", "Trópico de Capricornio"], "C"),
        ("¿Entre qué dos países se encuentran las cataratas del Iguazú?", ["Argentina y Brasil", "Argentina y Chile", "Brasil y Uruguay", "Chile y Bolivia"], "A"),
        ("¿Cuál es la montaña más alta sobre el nivel del mar?", ["Aconcagua", "Kilimanjaro", "Everest", "Mont Blanc"], "C"),
        ("¿Qué dos países sudamericanos no tienen salida al mar?", ["Bolivia y Paraguay", "Perú y Ecuador", "Chile y Bolivia", "Paraguay y Uruguay"], "A"),
        ("¿En qué mar desemboca el río Danubio?", ["Mar Báltico", "Mar Negro", "Mar Caspio", "Mar del Norte"], "B"),
        ("¿Cuál es la capital de Kenia?", ["Kampala", "Nairobi", "Dodoma", "Kigali"], "B"),
        ("¿Entre qué dos países se encuentra principalmente el lago Titicaca?", ["Chile y Argentina", "Perú y Bolivia", "Ecuador y Perú", "Bolivia y Paraguay"], "B"),
        ("¿Cuál es el lago más profundo del mundo?", ["Lago Superior", "Lago Victoria", "Lago Baikal", "Lago Tanganica"], "C"),
        ("¿Qué representan las líneas llamadas paralelos en un mapa?", ["Longitudes", "Latitudes", "Altitudes", "Husos horarios"], "B"),
        ("¿Qué canal artificial conecta el mar Mediterráneo con el mar Rojo?", ["Canal de Panamá", "Canal de Suez", "Canal de Kiel", "Canal de Corinto"], "B"),
        ("¿Qué cordillera marca gran parte de la frontera natural entre Francia y España?", ["Apeninos", "Pirineos", "Cárpatos", "Balcanes"], "B"),
        ("¿En qué país se encuentra la región de Capadocia, conocida por sus formaciones rocosas?", ["Grecia", "Turquía", "Jordania", "Irán"], "B"),
        ("¿Qué gran valle tectónico atraviesa el este de África?", ["Valle del Indo", "Gran Valle del Rift", "Valle del Loira", "Valle de Ferganá"], "B"),
    ],
    "matematica": [
        ("¿Cuánto es 7 × 8?", ["48", "54", "56", "64"], "C"),
        ("¿Cuántos lados tiene un hexágono?", ["Cinco", "Seis", "Siete", "Ocho"], "B"),
        ("¿A cuántos metros equivalen 100 centímetros?", ["0,1 m", "1 m", "10 m", "100 m"], "B"),
        ("¿Cuánto suman los ángulos interiores de un triángulo?", ["90°", "180°", "270°", "360°"], "B"),
        ("¿Cuánto es 3 al cuadrado?", ["6", "9", "12", "27"], "B"),
        ("¿Cuál es la expresión decimal de un medio?", ["0,2", "0,25", "0,5", "1,5"], "C"),
        ("¿Cuál es una aproximación de pi con dos decimales?", ["2,14", "3,14", "3,41", "4,13"], "B"),
        ("¿Cuál es el perímetro de un cuadrado de lado 5 cm?", ["10 cm", "15 cm", "20 cm", "25 cm"], "C"),
        ("¿Cuál es la raíz cuadrada de 81?", ["7", "8", "9", "10"], "C"),
        ("¿Cuánto es el 25 % de 200?", ["25", "40", "50", "75"], "C"),
        ("¿Cuáles son las soluciones de x² − 5x + 6 = 0?", ["1 y 6", "2 y 3", "−2 y −3", "3 y 5"], "B"),
        ("¿Cuánto es 3/4 dividido por 1/2?", ["3/8", "2/3", "1", "3/2"], "D"),
        ("Al lanzar un dado justo de seis caras, ¿cuál es la probabilidad de obtener un número mayor que 4?", ["1/6", "1/3", "1/2", "2/3"], "B"),
        ("¿Cuál es el área de un círculo de radio 3 unidades?", ["6π", "9π", "12π", "18π"], "B"),
        ("¿Qué número continúa la secuencia 2, 6, 18, 54...?", ["108", "126", "162", "216"], "C"),
        ("¿Cuánto es el 15 % de 240?", ["24", "30", "36", "40"], "C"),
        ("¿Cuál es la mediana de 3, 5, 8, 11 y 20?", ["5", "8", "9,4", "11"], "B"),
        ("¿Cuánto vale 2⁵ × 2³?", ["64", "128", "256", "512"], "C"),
        ("Un triángulo rectángulo tiene catetos de 3 y 4 unidades. ¿Cuánto mide la hipotenusa?", ["5", "6", "7", "8"], "A"),
        ("Si 3x + 7 = 25, ¿cuánto vale x?", ["4", "6", "8", "10"], "B"),
    ],
}

# Convierte el banco de ejemplo al formato que MongoDB usa para guardar preguntas.
PREGUNTAS_INICIALES = [
    {
        "categoria": categoria["id"],
        "orden": orden,
        "texto": texto,
        "opciones": [
            {"letra": letra, "texto": opcion}
            for letra, opcion in zip("ABCD", opciones)
        ],
        "respuesta_correcta": respuesta_correcta,
    }
    for categoria in CATEGORIAS
    for orden, (texto, opciones, respuesta_correcta) in enumerate(
        BANCO_PREGUNTAS[categoria["id"]], start=1
    )
]


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

    def asegurar_preguntas_iniciales(self):
        # Agrega preguntas de ejemplo que todavía no existen. Así se puede
        # iniciar la aplicación con una base vacía sin duplicar las preguntas.
        categorias_completas = all(
            self.coleccion_preguntas.count_documents({"categoria": categoria["id"]})
            >= 20
            for categoria in CATEGORIAS
        )
        if categorias_completas and self.coleccion_preguntas.count_documents(
            {"categoria": {"$exists": False}}
        ) == 0:
            return

        operaciones = [
            UpdateOne(
                {"texto": pregunta["texto"]},
                {
                    "$set": {
                        "categoria": pregunta["categoria"],
                        "orden": pregunta["orden"],
                    },
                    "$setOnInsert": {
                        "opciones": pregunta["opciones"],
                        "respuesta_correcta": pregunta["respuesta_correcta"],
                    },
                },
                upsert=True,
            )
            for pregunta in PREGUNTAS_INICIALES
        ]
        self.coleccion_preguntas.bulk_write(operaciones)

    def obtener_preguntas_para_quiz(self, categoria):
        self.asegurar_preguntas_iniciales()
        # MongoDB elige al azar diez preguntas de la categoría seleccionada.
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
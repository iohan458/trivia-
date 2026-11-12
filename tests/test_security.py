import unittest

from app import CATEGORIAS, PREGUNTAS_INICIALES, Pregunta, create_app


class RepositorioDePrueba:
    def __init__(self):
        ciencia = [
            documento
            for documento in PREGUNTAS_INICIALES
            if documento["categoria"] == "ciencia"
        ]
        self.preguntas = [
            Pregunta(
                str(indice),
                documento["texto"],
                documento["opciones"],
                documento["respuesta_correcta"],
                documento["categoria"],
            )
            for indice, documento in enumerate(ciencia[:10])
        ]
        self.exclusion_recibida = None
        self.fallar_al_obtener = False

    def obtener_preguntas_para_quiz(self, categoria):
        if self.fallar_al_obtener:
            raise RuntimeError("detalle interno de prueba")
        return self.preguntas

    def obtener_preguntas_por_ids(self, identificadores):
        return [self.preguntas[int(identificador)] for identificador in identificadores]

    def guardar_puntuacion(self, puntuacion):
        pass

    def obtener_mejor_puntuacion(self, nombre, categoria=None):
        return None

    def obtener_top10(self, categoria=None, excluir_nombre=None):
        self.exclusion_recibida = excluir_nombre
        return []


class SeguridadApiTest(unittest.TestCase):
    def setUp(self):
        self.repositorio = RepositorioDePrueba()
        self.app = create_app(self.repositorio)
        self.app.config.update(TESTING=True, SECRET_KEY="clave-de-prueba")
        self.client = self.app.test_client()

    def test_sanitiza_nombre_antes_de_guardarlo_en_la_sesion(self):
        respuesta = self.client.post(
            "/api/quiz/iniciar",
            json={"nombre": "<script>", "categoria": CATEGORIAS[0]["id"]},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json["jugador"], "<script>")
        with self.client.session_transaction() as sesion:
            self.assertEqual(sesion["jugador"], "&lt;script&gt;")

    def test_rechaza_json_con_formato_o_categoria_invalidos(self):
        respuesta_json = self.client.post("/api/quiz/iniciar", json=[])
        respuesta_categoria = self.client.post(
            "/api/quiz/iniciar",
            json={"nombre": "Ana", "categoria": {"$ne": None}},
        )

        self.assertEqual(respuesta_json.status_code, 400)
        self.assertEqual(respuesta_categoria.status_code, 400)

    def test_devuelve_error_generico_si_ocurre_un_error_interno(self):
        self.repositorio.fallar_al_obtener = True

        respuesta = self.client.post(
            "/api/quiz/iniciar",
            json={"nombre": "Ana", "categoria": CATEGORIAS[0]["id"]},
        )

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(
            respuesta.json,
            {"error": "Ocurrió un error interno. Intentá nuevamente más tarde."},
        )
        self.assertNotIn("detalle interno de prueba", respuesta.get_data(as_text=True))

    def test_sanitiza_nombres_usados_en_filtros_del_ranking(self):
        respuesta = self.client.get("/api/ranking?excluir=%3Cscript%3E")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.repositorio.exclusion_recibida, "&lt;script&gt;")


if __name__ == "__main__":
    unittest.main()

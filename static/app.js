// Estas referencias conectan el código con los campos y paneles de la página.
const startForm = document.querySelector("#start-form");
const nameInput = document.querySelector("#player-name");
const welcomePanel = document.querySelector("#welcome-panel");
const categoryPanel = document.querySelector("#category-panel");
const categoryGrid = document.querySelector("#category-grid");
const categoryPlayer = document.querySelector("#category-player");
const categoryError = document.querySelector("#category-error");
const quizPanel = document.querySelector("#quiz-panel");
const resultPanel = document.querySelector("#result-panel");
const questionCounter = document.querySelector("#question-counter");
const questionText = document.querySelector("#question-text");
const optionsContainer = document.querySelector("#answer-options");
const answerFeedback = document.querySelector("#answer-feedback");
const nextButton = document.querySelector("#next-button");
const liveScore = document.querySelector("#live-score");
const progressBar = document.querySelector("#progress-bar");
const finalScore = document.querySelector("#final-score");
const resultTitle = document.querySelector("#result-title");
const resultCopy = document.querySelector("#result-copy");
const gameError = document.querySelector("#game-error");
const startError = document.querySelector("#start-error");
const activeCategory = document.querySelector("#active-category");
const leaderboardDialog = document.querySelector("#leaderboard-dialog");
const leaderboardSubtitle = document.querySelector("#leaderboard-subtitle");
const leaderboardStatus = document.querySelector("#leaderboard-status");
const leaderboardTable = document.querySelector("#leaderboard-table");
const leaderboardRows = document.querySelector("#leaderboard-rows");

let currentQuestion = null;
let currentScore = 0;
let playerName = "";
let currentCategory = null;
let lastResult = null;

// Pide información al servidor y convierte una respuesta de error en un mensaje legible.
async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Ocurrió un error inesperado.");
  return data;
}

// Actualiza el marcador y dibuja en pantalla una pregunta con sus opciones.
function showQuestion(question, number, total, score) {
  currentQuestion = question;
  currentScore = score;
  questionCounter.textContent = `PREGUNTA ${number} DE ${total}`;
  questionText.textContent = question.texto;
  liveScore.textContent = score;
  progressBar.style.width = `${((number - 1) / total) * 100}%`;
  answerFeedback.hidden = true;
  answerFeedback.classList.remove("is-wrong");
  nextButton.hidden = true;
  optionsContainer.replaceChildren();

  for (const opcion of question.opciones) {
    const button = document.createElement("button");
    button.className = "answer-option";
    button.type = "button";
    button.dataset.letra = opcion.letra;

    const letter = document.createElement("span");
    letter.className = "option-letter";
    letter.textContent = opcion.letra;

    const text = document.createElement("span");
    text.className = "option-text";
    text.textContent = opcion.texto;

    button.append(letter, text);
    button.addEventListener("click", () => submitAnswer(opcion.letra));
    optionsContainer.append(button);
  }
}

// Al escribir el nombre, pide las categorías y pasa a la pantalla de selección.
async function startGame(event) {
  event.preventDefault();
  startError.textContent = "";
  gameError.textContent = "";
  playerName = nameInput.value.trim();
  const button = startForm.querySelector("button");
  button.disabled = true;

  try {
    const categories = await requestJson("/api/categorias");
    renderCategories(categories);
    categoryPlayer.textContent = `PARTIDA DE ${playerName.toLocaleUpperCase("es")}`;
    welcomePanel.hidden = true;
    categoryPanel.hidden = false;
    resultPanel.hidden = true;
    categoryPanel.querySelector("h2").focus();
  } catch (error) {
    startError.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

// Crea un botón por cada categoría recibida del servidor.
function renderCategories(categories) {
  categoryGrid.replaceChildren();
  for (const category of categories) {
    const button = document.createElement("button");
    button.className = "category-card";
    button.type = "button";

    const icon = document.createElement("span");
    icon.className = "category-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = category.icono;

    const name = document.createElement("strong");
    name.className = "category-name";
    name.textContent = category.nombre;

    const description = document.createElement("span");
    description.className = "category-description";
    description.textContent = category.descripcion;

    button.append(icon, name, description);
    button.addEventListener("click", () => startCategoryGame(category));
    categoryGrid.append(button);
  }
}

// Inicia una partida en la categoría elegida y muestra la primera pregunta.
async function startCategoryGame(category) {
  categoryError.textContent = "";
  const buttons = [...categoryGrid.querySelectorAll("button")];
  buttons.forEach((button) => { button.disabled = true; });

  try {
    const game = await requestJson("/api/quiz/iniciar", {
      method: "POST",
      body: JSON.stringify({ nombre: playerName, categoria: category.id }),
    });
    currentCategory = category;
    activeCategory.textContent = `${category.icono} ${category.nombre}`;
    categoryPanel.hidden = true;
    quizPanel.hidden = false;
    showQuestion(game.pregunta, game.numero_pregunta, game.total_preguntas, game.puntuacion);
  } catch (error) {
    categoryError.textContent = error.message;
    buttons.forEach((button) => { button.disabled = false; });
  }
}

// Envía la opción elegida, muestra si fue correcta y actualiza los puntos.
async function submitAnswer(letra) {
  const buttons = [...optionsContainer.querySelectorAll("button")];
  buttons.forEach((button) => { button.disabled = true; });
  gameError.textContent = "";

  try {
    const result = await requestJson("/api/quiz/responder", {
      method: "POST",
      body: JSON.stringify({ respuesta: letra }),
    });
    currentScore = result.puntuacion;
    liveScore.textContent = currentScore;
    progressBar.style.width = `${(result.numero_pregunta / result.total_preguntas) * 100}%`;
    for (const button of buttons) {
      if (button.dataset.letra === result.respuesta_correcta) button.classList.add("is-correct");
      else if (button.dataset.letra === letra && !result.correcta) button.classList.add("is-wrong");
    }

    answerFeedback.classList.toggle("is-wrong", !result.correcta);
    answerFeedback.textContent = result.correcta
      ? "¡Correcto! Sumaste 100 puntos."
      : `No era esa. La respuesta correcta era ${result.respuesta_correcta}.`;
    answerFeedback.hidden = false;
    lastResult = result;

    if (result.terminado) {
      nextButton.textContent = "Ver resultado →";
      nextButton.dataset.final = "true";
    } else {
      nextButton.textContent = "Continuar →";
      delete nextButton.dataset.final;
    }
    nextButton.hidden = false;
  } catch (error) {
    buttons.forEach((button) => { button.disabled = false; });
    gameError.textContent = error.message;
  }
}

// Avanza a la pregunta siguiente o presenta el resultado al llegar al final.
function continueGame() {
  if (!lastResult) return;
  if (lastResult.terminado) {
    showResult(lastResult);
    return;
  }
  showQuestion(
    lastResult.siguiente_pregunta,
    lastResult.numero_pregunta + 1,
    lastResult.total_preguntas,
    lastResult.puntuacion,
  );
}

// Muestra el puntaje final y un resumen de la partida completada.
function showResult(result) {
  quizPanel.hidden = true;
  resultPanel.hidden = false;
  finalScore.textContent = result.puntuacion;
  resultTitle.textContent = result.puntuacion === 1000 ? "¡Puntaje perfecto!" : "¡Buen trabajo!";
  resultCopy.textContent = `${playerName}, completaste las 10 preguntas de ${currentCategory.nombre}. Tu mejor puntuación es ${result.mejor_puntuacion?.puntuacion ?? result.puntuacion}/1000.`;
}

// Esta función se ejecuta al pulsar "Mostrar ranking" en la pantalla final.
async function showLeaderboard() {
  leaderboardSubtitle.textContent = currentCategory
    ? `TOP 10 · ${currentCategory.nombre.toLocaleUpperCase("es")}`
    : "TOP 10 · TODAS LAS CATEGORÍAS";
  leaderboardRows.replaceChildren();
  leaderboardTable.hidden = true;
  leaderboardStatus.hidden = false;
  leaderboardStatus.textContent = "Cargando resultados...";
  leaderboardDialog.showModal();

  try {
    const params = new URLSearchParams();
    if (currentCategory) params.set("categoria", currentCategory.id);
    if (playerName) params.set("excluir", playerName);
    const data = await requestJson(`/api/ranking?${params.toString()}`);

    if (data.top10.length === 0) {
      leaderboardStatus.textContent = "Todavía no hay resultados de otros jugadores.";
      return;
    }

    const nombresCategorias = {
      ciencia: "Ciencia",
      deportes: "Deportes",
      arte: "Arte",
      historia: "Historia",
      geografia: "Geografía",
      matematica: "Matemática",
    };
    for (const resultado of data.top10.slice(0, 10)) {
      const row = document.createElement("tr");
      const cells = [
        String(resultado.puesto).padStart(2, "0"),
        resultado.nombre,
        nombresCategorias[resultado.categoria] || "General",
        `${resultado.puntuacion}/${resultado.total}`,
      ];
      for (const value of cells) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      leaderboardRows.append(row);
    }

    leaderboardStatus.hidden = true;
    leaderboardTable.hidden = false;
  } catch (error) {
    leaderboardStatus.textContent = error.message;
  }
}

// Conecta los botones con las acciones que hacen avanzar o cerrar las pantallas.
startForm.addEventListener("submit", startGame);
nextButton.addEventListener("click", continueGame);
document.querySelector("#back-to-name").addEventListener("click", () => {
  categoryPanel.hidden = true;
  welcomePanel.hidden = false;
  nameInput.focus();
});
document.querySelector("#play-again-button").addEventListener("click", () => {
  resultPanel.hidden = true;
  categoryPanel.hidden = true;
  welcomePanel.hidden = false;
  currentCategory = null;
  nameInput.value = playerName;
  nameInput.focus();
});
document.querySelector("#ranking-focus-button").addEventListener("click", showLeaderboard);
document.querySelector("#close-leaderboard").addEventListener("click", () => leaderboardDialog.close());
leaderboardDialog.addEventListener("click", (event) => {
  if (event.target === leaderboardDialog) leaderboardDialog.close();
});
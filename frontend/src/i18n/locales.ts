// =============================================================================
// LOCALES — весь текст игры в одном файле.
// Добавить язык: скопируй блок `en`, задай новый ключ, переведи строки.
// Динамические строки — это функции: (n: number) => `... ${n} ...`
// =============================================================================

export type Locale = "en" | "ru";

export const locales = {
  // ---------------------------------------------------------------------------
  // English
  // ---------------------------------------------------------------------------
  en: {
    // ---- App header ----------------------------------------------------------
    appTitle: "♠ Durak",
    openRules: "Open game rules",
    gameRulesTitle: "Game rules",
    connected: "Connected",
    disconnected: "Disconnected",
    connectionLost: "Connection lost",
    backToMenu: "Back to menu",

    // ---- Lobby ---------------------------------------------------------------
    lobbyHeading: "Durak — Join a game",
    labelName: "Your name",
    placeholderName: "e.g. Alice",
    labelRoom: "Room code (leave blank to create)",
    placeholderRoom: "e.g. ABC123",
    btnJoin: "Join",
    btnCreateJoin: "Create & Join",
    rosterHeading: (n: number) => `Players (${n})`,
    tagHost: "Host",
    btnStart: "Start game",
    startDisabledHint: "Need at least 2 players",
    waitingForHost: "Waiting for host to start…",
    connecting: "Connecting…",

    // ---- Game over -----------------------------------------------------------
    gameOverHeading: "Game over",
    gameOverBody: "The last player holding cards loses:",
    btnBackToLobby: "Back to lobby",

    // ---- Action bar ----------------------------------------------------------
    btnPlayCard: "Play card",
    btnTakeBottom: "Take bottom",
    waitingForTurn: "Waiting for your turn…",
    waitingContribute: "Waiting for others to contribute…",
    pickContribute: "Pick a card to contribute to the buffer:",
    btnContribute: "Contribute",

    // ---- Table ---------------------------------------------------------------
    trumpTitle: "Current trump suit",
    trumpLabel: "Trump",
    stackEmpty: "Empty — waiting for opener",
    chipBito: (n: number) => `Bito: ${n}`,
    chipBuffer: (n: number) => `Buffer: ${n}`,
    chipBufferDealt: "Buffer dealt",

    // ---- Player list ---------------------------------------------------------
    tagTurn: "Turn",
    cardCount: (n: number) => `${n} cards`,

    // ---- Player badge --------------------------------------------------------
    hiddenCount: (n: number) => `hidden: ${n}`,

    // ---- Rules modal ---------------------------------------------------------
    rulesHeading: "Rules",
    closeRules: "Close rules",
    rulesLines: [
      "Goal: avoid being the last player who still has cards. The last remaining player loses.",
      "The game supports 2 to 5 players.",
      "The first card is placed automatically when the game starts.",
      "On your turn, play one card that beats the current top card on the table.",
      "A higher card of the same suit beats a lower one.",
      "A trump card beats any non-trump card.",
      "Spades are special: only a higher spade can beat a spade.",
      "If you cannot or do not want to beat, press Take bottom.",
      "That takes the bottom table card into your main hand and passes the turn.",
      "When the table stack reaches the number of active players, it is cleared as bito.",
      "In 2 to 3 player games, bito can trigger a shared buffer mechanic.",
      "During contribution, each active player sends one main-hand card into the buffer.",
      "After buffer distribution, players may move from main cards to buffer cards.",
      "When a player finishes buffer cards, their hidden cards are revealed.",
      "When a player runs out of hidden cards, they are out of the game.",
    ],

    // ---- Toast messages ------------------------------------------------------
    toastConnected: "Connected",
    toastReconnecting: (secs: number) => `Reconnecting in ${secs}s…`,
    toastGaveUp: "Connection lost — gave up reconnecting",
    toastGameStarted: (trump: string) => `Game started — trump is ${trump}`,
    toastBito: (n: number) => `Stack cleared (bito #${n})`,
    toastContributeRequest: "Choose a card to contribute to the buffer",
    toastBufferTriggered: (trump: string) => `Buffer distributed — new trump is ${trump}`,
    toastBufferShare: "You received your buffer share",
    toastHiddenRevealed: "Your hidden cards are revealed",
    toastForcedTake: "Forced to take the bottom card",
    toastPlayerOut: (name: string) => `${name} is out`,
    toastTurnSkipped: "Turn skipped (hidden cards revealed)",
    toastNotConnected: "Not connected",
    toastMalformed: "Received malformed message",
  },

  // ---------------------------------------------------------------------------
  // Русский
  // ---------------------------------------------------------------------------
  ru: {
    // ---- Хедер ---------------------------------------------------------------
    appTitle: "♠ Дурак",
    openRules: "Открыть правила",
    gameRulesTitle: "Правила",
    connected: "Подключено",
    disconnected: "Отключено",
    connectionLost: "Соединение потеряно",
    backToMenu: "Вернуться в меню",

    // ---- Лобби ---------------------------------------------------------------
    lobbyHeading: "Дурак — Войти в игру",
    labelName: "Ваше имя",
    placeholderName: "напр. Алиса",
    labelRoom: "Код комнаты (оставьте пустым, чтобы создать)",
    placeholderRoom: "напр. ABC123",
    btnJoin: "Войти",
    btnCreateJoin: "Создать и войти",
    rosterHeading: (n: number) => `Игроки (${n})`,
    tagHost: "Хост",
    btnStart: "Начать игру",
    startDisabledHint: "Нужно минимум 2 игрока",
    waitingForHost: "Ожидание хоста…",
    connecting: "Подключение…",

    // ---- Конец игры ----------------------------------------------------------
    gameOverHeading: "Игра окончена",
    gameOverBody: "Последний игрок с картами на руках проигрывает:",
    btnBackToLobby: "В лобби",

    // ---- Панель действий -----------------------------------------------------
    btnPlayCard: "Играть карту",
    btnTakeBottom: "Взять нижнюю",
    waitingForTurn: "Ждите своего хода…",
    waitingContribute: "Ожидание других игроков…",
    pickContribute: "Выберите карту для буфера:",
    btnContribute: "Отдать",

    // ---- Стол ----------------------------------------------------------------
    trumpTitle: "Текущий козырь",
    trumpLabel: "Козырь",
    stackEmpty: "Стол пуст — ожидание первого хода",
    chipBito: (n: number) => `Бито: ${n}`,
    chipBuffer: (n: number) => `Буфер: ${n}`,
    chipBufferDealt: "Буфер роздан",

    // ---- Список игроков ------------------------------------------------------
    tagTurn: "Ход",
    cardCount: (n: number) => `${n} карт`,

    // ---- Значок скрытых карт -------------------------------------------------
    hiddenCount: (n: number) => `скрытых: ${n}`,

    // ---- Модалка правил ------------------------------------------------------
    rulesHeading: "Правила",
    closeRules: "Закрыть правила",
    rulesLines: [
      "Цель: не быть последним с картами на руках. Последний игрок проигрывает.",
      "Игра поддерживает от 2 до 5 игроков.",
      "Первая карта кладётся автоматически при старте игры.",
      "В свой ход сыграйте карту, которая бьёт верхнюю карту на столе.",
      "Старшая карта той же масти бьёт младшую.",
      "Козырная карта бьёт любую некозырную.",
      "Пики особенные: только старшая пика бьёт пику.",
      "Если не можете или не хотите бить — нажмите «Взять нижнюю».",
      "Это возьмёт нижнюю карту стола в основную руку и передаст ход.",
      "Когда стопка достигает числа активных игроков — она уходит в бито.",
      "В игре 2–3 игроков бито может запустить механику буфера.",
      "При взносе каждый активный игрок отдаёт одну карту из основной руки в буфер.",
      "После раздачи буфера игроки переходят с основных карт на буферные.",
      "Когда игрок заканчивает буферные карты — раскрываются его скрытые карты.",
      "Когда у игрока заканчиваются скрытые карты — он выбывает.",
    ],

    // ---- Toast-сообщения -----------------------------------------------------
    toastConnected: "Подключено",
    toastReconnecting: (secs: number) => `Переподключение через ${secs}с…`,
    toastGaveUp: "Соединение потеряно — попытки исчерпаны",
    toastGameStarted: (trump: string) => `Игра началась — козырь ${trump}`,
    toastBito: (n: number) => `Стопка сброшена (бито #${n})`,
    toastContributeRequest: "Выберите карту для взноса в буфер",
    toastBufferTriggered: (trump: string) => `Буфер роздан — новый козырь ${trump}`,
    toastBufferShare: "Вы получили свою долю буфера",
    toastHiddenRevealed: "Ваши скрытые карты раскрыты",
    toastForcedTake: "Вы вынуждены взять нижнюю карту",
    toastPlayerOut: (name: string) => `${name} выбывает`,
    toastTurnSkipped: "Ход пропущен (раскрытие скрытых карт)",
    toastNotConnected: "Нет соединения",
    toastMalformed: "Получено некорректное сообщение",
  },
} as const satisfies Record<Locale, object>;

export type Strings = typeof locales.en;

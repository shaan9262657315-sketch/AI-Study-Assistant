import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { generateFlashcards, getPDFLibrary } from "../services/api";

export default function Flashcards() {
  // =====================================================
  // COMMON
  // =====================================================

  const [mode, setMode] = useState("topic");

  const [topic, setTopic] = useState("");

  const [pdfs, setPdfs] = useState([]);

  const [documentId, setDocumentId] = useState("");

  const [questionCount, setQuestionCount] = useState(10);

  // =====================================================
  // FLASHCARDS
  // =====================================================

  const [cards, setCards] = useState([]);

  const [currentIndex, setCurrentIndex] = useState(0);

  const [flipped, setFlipped] = useState(false);

  const [knownCards, setKnownCards] = useState([]);

  const [unknownCards, setUnknownCards] = useState([]);

  const [revisionMode, setRevisionMode] = useState(false);

  // =====================================================
  // STATE
  // =====================================================

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  // =====================================================
  // LOAD PDFs
  // =====================================================

  useEffect(() => {
    loadPDFs();
  }, []);

  const loadPDFs = async () => {
    try {
      const data = await getPDFLibrary();

      setPdfs(data);

      if (data.length > 0) {
        setDocumentId(data[0].document_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  // =====================================================
  // GENERATE FLASHCARDS
  // =====================================================

  const handleGenerate = async () => {
    setError("");

    // -----------------------------
    // VALIDATION
    // -----------------------------

    if (mode === "topic" && !topic.trim()) {
      setError("Please enter a topic.");
      return;
    }

    if (mode === "pdf" && !documentId) {
      setError("Please select a PDF.");
      return;
    }

    const count = Number(questionCount);

    if (count < 1 || count > 20) {
      setError("Number of flashcards must be between 1 and 20.");
      return;
    }

    // -----------------------------
    // RESET
    // -----------------------------

    setLoading(true);

    setCards([]);

    setCurrentIndex(0);

    setFlipped(false);

    setKnownCards([]);

    setUnknownCards([]);

    setRevisionMode(false);

    try {
      const data = await generateFlashcards({
        mode: mode,

        topic: topic.trim() || null,

        document_id: mode === "pdf" ? documentId : null,

        question_count: count,
      });

      setCards(data.flashcards || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // NEXT CARD
  // =====================================================

  const nextCard = () => {
    setFlipped(false);

    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCurrentIndex(cards.length);
    }
  };

  // =====================================================
  // PREVIOUS CARD
  // =====================================================

  const previousCard = () => {
    if (currentIndex > 0) {
      setFlipped(false);
      setCurrentIndex(currentIndex - 1);
    }
  };

  // =====================================================
  // MARK KNOWN
  // =====================================================

  const markKnown = () => {
    if (!cards[currentIndex]) return;

    if (!knownCards.includes(currentIndex)) {
      setKnownCards((prev) => [
        ...prev,
        currentIndex,
      ]);
    }

    setUnknownCards((prev) =>
      prev.filter((index) => index !== currentIndex)
    );

    nextCard();
  };

  // =====================================================
  // MARK UNKNOWN
  // =====================================================

  const markUnknown = () => {
    if (!cards[currentIndex]) return;

    if (!unknownCards.includes(currentIndex)) {
      setUnknownCards((prev) => [
        ...prev,
        currentIndex,
      ]);
    }

    setKnownCards((prev) =>
      prev.filter((index) => index !== currentIndex)
    );

    nextCard();
  };

  // =====================================================
  // REVISION MODE
  // =====================================================

  const startRevision = () => {
    const revisionCards = unknownCards.map(
      (index) => cards[index]
    );

    if (revisionCards.length === 0) {
      return;
    }

    setCards(revisionCards);

    setCurrentIndex(0);

    setFlipped(false);

    setKnownCards([]);

    setUnknownCards([]);

    setRevisionMode(true);
  };

  // =====================================================
  // RESET
  // =====================================================

  const resetFlashcards = () => {
    setCards([]);

    setCurrentIndex(0);

    setFlipped(false);

    setKnownCards([]);

    setUnknownCards([]);

    setRevisionMode(false);

    setError("");
  };

  // =====================================================
  // COMPLETED
  // =====================================================

  const completed =
    cards.length > 0 &&
    currentIndex >= cards.length;

  // =====================================================
  // PROGRESS
  // =====================================================

  const progress =
    cards.length > 0
      ? Math.round(
          (knownCards.length / cards.length) * 100
        )
      : 0;

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="min-h-screen bg-gray-100">

      {/* =================================================
          NAVBAR
      ================================================= */}

      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center">

        {/* BRAND */}
        <div>
          <h1 className="text-xl font-bold">
            🤖 AI Study Assistant
          </h1>

          <p className="text-xs text-indigo-100 mt-1">
            Powered by Shaan AI
          </p>
        </div>

        {/* DASHBOARD */}
        <Link
          to="/"
          className="bg-white text-indigo-600 px-5 py-2.5 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </Link>

      </nav>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="max-w-5xl mx-auto px-6 py-10">

        {/* =================================================
            HEADING
        ================================================= */}

        <div className="mb-8">

          <h2 className="text-4xl font-bold text-gray-900">
            🗂️ AI Flashcards
          </h2>

          <p className="text-xl text-gray-500 mt-3">
            Generate flashcards and revise important concepts.
          </p>

        </div>


        {/* =================================================
            GENERATOR
        ================================================= */}

        {!cards.length && (

          <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">

            {/* MODE BUTTONS */}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-7">

              {/* TOPIC MODE */}

              <button
                type="button"
                onClick={() => {
                  setMode("topic");
                  setError("");
                }}
                className={`p-6 rounded-2xl border-2 text-left transition ${
                  mode === "topic"
                    ? "border-indigo-600 bg-indigo-50"
                    : "border-gray-200 hover:border-indigo-300"
                }`}
              >

                <h3 className="text-xl font-bold text-gray-800">
                  🤖 Topic Flashcards
                </h3>

                <p className="text-gray-500 mt-2">
                  Enter any topic and generate AI flashcards.
                </p>

              </button>


              {/* PDF MODE */}

              <button
                type="button"
                onClick={() => {
                  setMode("pdf");
                  setError("");
                }}
                className={`p-6 rounded-2xl border-2 text-left transition ${
                  mode === "pdf"
                    ? "border-indigo-600 bg-indigo-50"
                    : "border-gray-200 hover:border-indigo-300"
                }`}
              >

                <h3 className="text-xl font-bold text-gray-800">
                  📚 My PDF Flashcards
                </h3>

                <p className="text-gray-500 mt-2">
                  Generate flashcards from your uploaded PDF.
                </p>

              </button>

            </div>


            {/* =================================================
                TOPIC MODE INPUT
            ================================================= */}

            {mode === "topic" && (

              <div className="mb-6">

                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Enter Topic
                </label>

                <input
                  type="text"
                  value={topic}
                  onChange={(e) => {
                    setTopic(e.target.value);
                    setError("");
                  }}
                  placeholder="Example: Java OOP"
                  className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
                />

              </div>

            )}


            {/* =================================================
                PDF MODE
            ================================================= */}

            {mode === "pdf" && (

              <div>

                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Select PDF
                </label>

                <select
                  value={documentId}
                  onChange={(e) =>
                    setDocumentId(e.target.value)
                  }
                  className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
                >

                  {pdfs.length === 0 ? (

                    <option value="">
                      No PDF available
                    </option>

                  ) : (

                    pdfs.map((pdf) => (

                      <option
                        key={pdf.document_id}
                        value={pdf.document_id}
                      >
                        {pdf.filename}
                      </option>

                    ))

                  )}

                </select>


                <label className="block text-sm font-semibold text-gray-700 mt-6 mb-2">
                  Topic (Optional)
                </label>

                <input
                  type="text"
                  value={topic}
                  onChange={(e) => {
                    setTopic(e.target.value);
                    setError("");
                  }}
                  placeholder="Example: Newton's Laws"
                  className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
                />

                <p className="text-sm text-gray-500 mt-2">
                  Leave empty to generate flashcards from
                  important concepts in the PDF.
                </p>

              </div>

            )}


            {/* =================================================
                QUESTION COUNT
            ================================================= */}

            <div className="mt-6">

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Number of Flashcards
              </label>

              <select
                value={questionCount}
                onChange={(e) =>
                  setQuestionCount(e.target.value)
                }
                className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
              >

                <option value="5">
                  5 Flashcards
                </option>

                <option value="10">
                  10 Flashcards
                </option>

                <option value="15">
                  15 Flashcards
                </option>

                <option value="20">
                  20 Flashcards
                </option>

              </select>

            </div>


            {/* =================================================
                ERROR
            ================================================= */}

            {error && (

              <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl">
                {error}
              </div>

            )}


            {/* =================================================
                GENERATE
            ================================================= */}

            <button
              onClick={handleGenerate}
              disabled={
                loading ||
                (mode === "pdf" && pdfs.length === 0)
              }
              className="w-full mt-7 bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-4 rounded-2xl transition disabled:opacity-60 disabled:cursor-not-allowed"
            >

              {loading
                ? "🤖 Generating Flashcards..."
                : "✨ Generate Flashcards"}

            </button>

          </div>

        )}


        {/* =================================================
            FLASHCARD
        ================================================= */}

        {cards.length > 0 && !completed && (

          <div className="mt-8">

            {/* PROGRESS HEADER */}

            <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-5 mb-5 flex justify-between items-center">

              <div>

                <p className="font-bold text-gray-800">
                  Card {currentIndex + 1} / {cards.length}
                </p>

                {revisionMode && (
                  <p className="text-sm text-indigo-600 mt-1">
                    🔄 Revision Mode
                  </p>
                )}

              </div>

              <div className="text-sm font-semibold text-gray-600">

                <span className="text-green-600">
                  ✅ {knownCards.length} Known
                </span>

                <span className="mx-2">
                  ·
                </span>

                <span className="text-red-600">
                  ❌ {unknownCards.length} Unknown
                </span>

              </div>

            </div>


            {/* FLASHCARD */}

            <div
              onClick={() => setFlipped(!flipped)}
              className={`min-h-[360px] bg-white rounded-3xl shadow-lg border border-gray-200 p-10 flex flex-col justify-center items-center text-center cursor-pointer hover:shadow-xl transition ${
                flipped ? "bg-indigo-50" : ""
              }`}
            >

              {!flipped ? (

                <>
                  <p className="text-sm font-bold text-indigo-600 tracking-widest mb-6">
                    QUESTION
                  </p>

                  <h3 className="text-3xl font-bold text-gray-900 leading-relaxed">
                    {cards[currentIndex].question}
                  </h3>

                  <p className="text-gray-500 mt-8">
                    👆 Click the card to reveal the answer
                  </p>
                </>

              ) : (

                <>
                  <p className="text-sm font-bold text-indigo-600 tracking-widest mb-6">
                    ANSWER
                  </p>

                  <p className="text-xl text-gray-700 leading-8 max-w-3xl whitespace-pre-wrap">
                    {cards[currentIndex].answer}
                  </p>

                  <p className="text-gray-500 mt-8">
                    👆 Click the card to see the question
                  </p>
                </>

              )}

            </div>


            {/* =================================================
                CONTROLS
            ================================================= */}

            <div className="flex flex-wrap gap-3 justify-center mt-6">

              {/* PREVIOUS */}

              <button
                onClick={previousCard}
                disabled={currentIndex === 0}
                className="px-5 py-3 rounded-xl bg-white border border-gray-300 font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Previous
              </button>


              {/* UNKNOWN */}

              <button
                onClick={markUnknown}
                className="px-6 py-3 rounded-xl bg-red-50 border border-red-200 text-red-600 font-semibold hover:bg-red-100 transition"
              >
                ❌ Unknown
              </button>


              {/* KNOWN */}

              <button
                onClick={markKnown}
                className="px-6 py-3 rounded-xl bg-green-50 border border-green-200 text-green-600 font-semibold hover:bg-green-100 transition"
              >
                ✅ Known
              </button>

            </div>

          </div>

        )}


        {/* =================================================
            COMPLETED
        ================================================= */}

        {completed && (

          <div className="mt-8 bg-white rounded-3xl shadow-lg border border-gray-200 p-10 text-center">

            <h2 className="text-3xl font-bold text-gray-900">
              🎉 Flashcards Completed!
            </h2>

            {revisionMode && (

              <p className="text-indigo-600 font-semibold mt-3">
                🔄 Revision session completed
              </p>

            )}


            {/* STATS */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-8">

              <div className="bg-green-50 border border-green-100 rounded-2xl p-5">

                <p className="text-sm text-green-600 font-semibold">
                  Known
                </p>

                <p className="text-3xl font-bold text-green-700 mt-2">
                  {knownCards.length}
                </p>

              </div>


              <div className="bg-red-50 border border-red-100 rounded-2xl p-5">

                <p className="text-sm text-red-600 font-semibold">
                  Unknown
                </p>

                <p className="text-3xl font-bold text-red-700 mt-2">
                  {unknownCards.length}
                </p>

              </div>


              <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-5">

                <p className="text-sm text-indigo-600 font-semibold">
                  Progress
                </p>

                <p className="text-3xl font-bold text-indigo-700 mt-2">
                  {progress}%
                </p>

              </div>

            </div>


            {/* =================================================
                ACTIONS
            ================================================= */}

            <div className="flex flex-wrap justify-center gap-4 mt-8">

              {unknownCards.length > 0 &&
                !revisionMode && (

                  <button
                    onClick={startRevision}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold transition"
                  >
                    🔄 Revise Unknown Cards
                  </button>

                )}


              <button
                onClick={resetFlashcards}
                className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-xl font-semibold transition"
              >
                ✨ Generate New Cards
              </button>

            </div>

          </div>

        )}

      </main>

    </div>
  );
}
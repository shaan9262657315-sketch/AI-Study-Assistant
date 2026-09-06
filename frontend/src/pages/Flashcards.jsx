import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getFlashcardLibrary, generateFlashcards, getPDFLibrary, deleteFlashcardSet } from "../services/api";

export default function Flashcards() {
  const [activeTab, setActiveTab] = useState("generate"); // "generate" or "library"
  const [library, setLibrary] = useState([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);

  const [mode, setMode] = useState("topic");
  const [topic, setTopic] = useState("");
  const [pdfs, setPdfs] = useState([]);
  const [documentId, setDocumentId] = useState("");
  const [questionCount, setQuestionCount] = useState(10);

  const [cards, setCards] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [knownCards, setKnownCards] = useState([]);
  const [unknownCards, setUnknownCards] = useState([]);
  const [revisionMode, setRevisionMode] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadPDFs();
    loadLibrary();
  }, []);

  const loadPDFs = async () => {
    try {
      const data = await getPDFLibrary();
      setPdfs(data);
      if (data && data.length > 0) {
        setDocumentId(data[0].document_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadLibrary = async () => {
    setLoadingLibrary(true);
    try {
      const data = await getFlashcardLibrary();
      setLibrary(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingLibrary(false);
    }
  };

  const handleGenerate = async () => {
    setError("");

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
      loadLibrary(); 
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteLibraryItem = async (id) => {
    try {
      await deleteFlashcardSet(id);
      setLibrary((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const nextCard = () => {
    setFlipped(false);
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCurrentIndex(cards.length);
    }
  };

  const previousCard = () => {
    if (currentIndex > 0) {
      setFlipped(false);
      setCurrentIndex(currentIndex - 1);
    }
  };

  const markKnown = () => {
    if (!cards[currentIndex]) return;
    if (!knownCards.includes(currentIndex)) {
      setKnownCards((prev) => [...prev, currentIndex]);
    }
    setUnknownCards((prev) => prev.filter((index) => index !== currentIndex));
    nextCard();
  };

  const markUnknown = () => {
    if (!cards[currentIndex]) return;
    if (!unknownCards.includes(currentIndex)) {
      setUnknownCards((prev) => [...prev, currentIndex]);
    }
    setKnownCards((prev) => prev.filter((index) => index !== currentIndex));
    nextCard();
  };

  const deleteCurrentCard = () => {
    if (cards.length <= 1) {
      resetFlashcards();
      return;
    }

    const updatedCards = cards.filter((_, index) => index !== currentIndex);
    setCards(updatedCards);

    setKnownCards((prev) =>
      prev.filter((i) => i !== currentIndex).map((i) => (i > currentIndex ? i - 1 : i))
    );
    setUnknownCards((prev) =>
      prev.filter((i) => i !== currentIndex).map((i) => (i > currentIndex ? i - 1 : i))
    );

    if (currentIndex >= updatedCards.length) {
      setCurrentIndex(updatedCards.length - 1);
    }
    setFlipped(false);
  };

  const startRevision = () => {
    const revisionCards = unknownCards.map((index) => cards[index]);
    if (revisionCards.length === 0) return;

    setCards(revisionCards);
    setCurrentIndex(0);
    setFlipped(false);
    setKnownCards([]);
    setUnknownCards([]);
    setRevisionMode(true);
  };

  const resetFlashcards = () => {
    setCards([]);
    setCurrentIndex(0);
    setFlipped(false);
    setKnownCards([]);
    setUnknownCards([]);
    setRevisionMode(false);
    setError("");
  };

  const completed = cards.length > 0 && currentIndex >= cards.length;
  const progress = cards.length > 0 ? Math.round((knownCards.length / cards.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold">🤖 AI Study Assistant</h1>
          <p className="text-xs text-indigo-100 mt-1">Powered by Shaan AI</p>
        </div>
        <Link to="/" className="bg-white text-indigo-600 px-5 py-2.5 rounded-xl font-semibold hover:bg-gray-100 transition">
          Dashboard
        </Link>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-4xl font-bold text-gray-900">🗂️ AI Flashcards</h2>
            <p className="text-xl text-gray-500 mt-2">Generate flashcards and manage your saved sets.</p>
          </div>
          <div className="flex bg-white p-1.5 rounded-2xl border border-gray-200 shadow-sm">
            <button
              onClick={() => setActiveTab("generate")}
              className={`px-5 py-2.5 rounded-xl font-semibold transition ${
                activeTab === "generate" ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              Generate New
            </button>
            <button
              onClick={() => { setActiveTab("library"); loadLibrary(); }}
              className={`px-5 py-2.5 rounded-xl font-semibold transition ${
                activeTab === "library" ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              📚 Saved Library
            </button>
          </div>
        </div>

        {activeTab === "library" ? (
          <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">
            <h3 className="text-2xl font-bold text-gray-800 mb-6">Saved Flashcard Sets</h3>
            {loadingLibrary ? (
              <p className="text-gray-500 text-center py-10">Loading saved library...</p>
            ) : library.length === 0 ? (
              <p className="text-gray-500 text-center py-10">No saved flashcard sets found.</p>
            ) : (
              <div className="space-y-4">
                {library.map((item, idx) => (
                  <div key={item.id || idx} className="flex justify-between items-center p-5 bg-gray-50 border border-gray-200 rounded-2xl">
                    <div>
                      <h4 className="font-bold text-lg text-gray-800">{item.topic || "Flashcard Set"}</h4>
                      <p className="text-sm text-gray-500 mt-1">Total Cards: {item.flashcards?.length || "N/A"}</p>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => {
                          setCards(item.flashcards || []);
                          setActiveTab("generate");
                        }}
                        className="px-4 py-2 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 font-semibold rounded-xl transition cursor-pointer"
                      >
                        Study
                      </button>
                      <button
                        onClick={() => deleteLibraryItem(item.id)}
                        className="px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 font-semibold rounded-xl transition cursor-pointer"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {!cards.length && (
              <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-7">
                  <button
                    type="button"
                    onClick={() => { setMode("topic"); setError(""); }}
                    className={`p-6 rounded-2xl border-2 text-left transition ${
                      mode === "topic" ? "border-indigo-600 bg-indigo-50" : "border-gray-200 hover:border-indigo-300"
                    }`}
                  >
                    <h3 className="text-xl font-bold text-gray-800">🤖 Topic Flashcards</h3>
                    <p className="text-gray-500 mt-2">Enter any topic and generate AI flashcards.</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => { setMode("pdf"); setError(""); }}
                    className={`p-6 rounded-2xl border-2 text-left transition ${
                      mode === "pdf" ? "border-indigo-600 bg-indigo-50" : "border-gray-200 hover:border-indigo-300"
                    }`}
                  >
                    <h3 className="text-xl font-bold text-gray-800">📚 My PDF Flashcards</h3>
                    <p className="text-gray-500 mt-2">Generate flashcards from your uploaded PDF.</p>
                  </button>
                </div>

                {mode === "topic" && (
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Enter Topic</label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => { setTopic(e.target.value); setError(""); }}
                      placeholder="Example: Data Structures & Algorithms"
                      className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
                    />
                  </div>
                )}

                {mode === "pdf" && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Select PDF</label>
                    <select
                      value={documentId}
                      onChange={(e) => setDocumentId(e.target.value)}
                      className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition bg-white"
                    >
                      {pdfs.length === 0 ? (
                        <option value="">No PDF available</option>
                      ) : (
                        pdfs.map((pdf) => (
                          <option key={pdf.document_id} value={pdf.document_id}>{pdf.filename}</option>
                        ))
                      )}
                    </select>

                    <label className="block text-sm font-semibold text-gray-700 mt-6 mb-2">Topic (Optional)</label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => { setTopic(e.target.value); setError(""); }}
                      placeholder="Example: Trees and Graphs"
                      className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
                    />
                  </div>
                )}

                <div className="mt-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Number of Flashcards</label>
                  <select
                    value={questionCount}
                    onChange={(e) => setQuestionCount(e.target.value)}
                    className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition bg-white"
                  >
                    <option value="5">5 Flashcards</option>
                    <option value="10">10 Flashcards</option>
                    <option value="15">15 Flashcards</option>
                    <option value="20">20 Flashcards</option>
                  </select>
                </div>

                {error && <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl">{error}</div>}

                <button
                  onClick={handleGenerate}
                  disabled={loading || (mode === "pdf" && pdfs.length === 0)}
                  className="w-full mt-7 bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-4 rounded-2xl transition disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                >
                  {loading ? "🤖 Generating Flashcards..." : "✨ Generate Flashcards"}
                </button>
              </div>
            )}

            {cards.length > 0 && !completed && (
              <div className="mt-8">
                <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-5 mb-5 flex justify-between items-center">
                  <div>
                    <p className="font-bold text-gray-800">Card {currentIndex + 1} / {cards.length}</p>
                    {revisionMode && <p className="text-sm text-indigo-600 mt-1">🔄 Revision Mode</p>}
                  </div>
                  <div className="text-sm font-semibold text-gray-600">
                    <span className="text-green-600">✅ {knownCards.length} Known</span>
                    <span className="mx-2">·</span>
                    <span className="text-red-600">❌ {unknownCards.length} Unknown</span>
                  </div>
                </div>

                <div
                  onClick={() => setFlipped(!flipped)}
                  className={`min-h-[360px] bg-white rounded-3xl shadow-lg border border-gray-200 p-10 flex flex-col justify-center items-center text-center cursor-pointer hover:shadow-xl transition ${
                    flipped ? "bg-indigo-50" : ""
                  }`}
                >
                  {!flipped ? (
                    <>
                      <p className="text-sm font-bold text-indigo-600 tracking-widest mb-6">QUESTION</p>
                      <h3 className="text-3xl font-bold text-gray-900 leading-relaxed">{cards[currentIndex].question}</h3>
                      <p className="text-gray-500 mt-8">👆 Click the card to reveal the answer</p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-bold text-indigo-600 tracking-widest mb-6">ANSWER</p>
                      <p className="text-xl text-gray-700 leading-8 max-w-3xl whitespace-pre-wrap">{cards[currentIndex].answer}</p>
                      <p className="text-gray-500 mt-8">👆 Click the card to see the question</p>
                    </>
                  )}
                </div>

                <div className="flex flex-wrap gap-3 justify-center mt-6">
                  <button
                    onClick={previousCard}
                    disabled={currentIndex === 0}
                    className="px-5 py-3 rounded-xl bg-white border border-gray-300 font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    ← Previous
                  </button>
                  <button
                    onClick={deleteCurrentCard}
                    className="px-5 py-3 rounded-xl bg-gray-100 border border-gray-300 text-gray-600 font-semibold hover:bg-gray-200 transition cursor-pointer"
                  >
                    🗑️ Delete Card
                  </button>
                  <button
                    onClick={markUnknown}
                    className="px-6 py-3 rounded-xl bg-red-50 border border-red-200 text-red-600 font-semibold hover:bg-red-100 transition cursor-pointer"
                  >
                    ❌ Unknown
                  </button>
                  <button
                    onClick={markKnown}
                    className="px-6 py-3 rounded-xl bg-green-50 border border-green-200 text-green-600 font-semibold hover:bg-green-100 transition cursor-pointer"
                  >
                    ✅ Known
                  </button>
                </div>
              </div>
            )}

            {completed && (
              <div className="mt-8 bg-white rounded-3xl shadow-lg border border-gray-200 p-10 text-center">
                <h2 className="text-3xl font-bold text-gray-900">🎉 Flashcards Completed!</h2>
                {revisionMode && <p className="text-indigo-600 font-semibold mt-3">🔄 Revision session completed</p>}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-8">
                  <div className="bg-green-50 border border-green-100 rounded-2xl p-5">
                    <p className="text-sm text-green-600 font-semibold">Known</p>
                    <p className="text-3xl font-bold text-green-700 mt-2">{knownCards.length}</p>
                  </div>
                  <div className="bg-red-50 border border-red-100 rounded-2xl p-5">
                    <p className="text-sm text-red-600 font-semibold">Unknown</p>
                    <p className="text-3xl font-bold text-red-700 mt-2">{unknownCards.length}</p>
                  </div>
                  <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-5">
                    <p className="text-sm text-indigo-600 font-semibold">Progress</p>
                    <p className="text-3xl font-bold text-indigo-700 mt-2">{progress}%</p>
                  </div>
                </div>

                <div className="flex flex-wrap justify-center gap-4 mt-8">
                  {unknownCards.length > 0 && !revisionMode && (
                    <button
                      onClick={startRevision}
                      className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold transition cursor-pointer"
                    >
                      🔄 Revise Unknown Cards
                    </button>
                  )}
                  <button
                    onClick={resetFlashcards}
                    className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-xl font-semibold transition cursor-pointer"
                  >
                    ✨ Generate New Cards
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
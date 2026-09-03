import { useEffect, useState } from "react";
import { generateFlashcards, getPDFLibrary } from "../services/api";


export default function Flashcards() {

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

  }, []);


  const loadPDFs = async () => {

    try {

      const data = await getPDFLibrary();

      setPdfs(data);

    } catch (err) {

      console.error(err);

    }

  };


  const handleGenerate = async () => {

    setError("");

    setLoading(true);

    setCards([]);

    setCurrentIndex(0);

    setFlipped(false);

    setKnownCards([]);

    setUnknownCards([]);

    setRevisionMode(false);

    try {

      const data = await generateFlashcards({

        mode,

        topic: mode === "topic" ? topic : topic || null,

        document_id:
          mode === "pdf" ? documentId : null,

        question_count: Number(questionCount)

      });

      setCards(data.flashcards);

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }
  };


  const markKnown = () => {

    const card = cards[currentIndex];

    if (!card) return;

    if (!knownCards.includes(currentIndex)) {

      setKnownCards([
        ...knownCards,
        currentIndex
      ]);

    }

    setUnknownCards(
      unknownCards.filter(
        index => index !== currentIndex
      )
    );

    nextCard();
  };


  const markUnknown = () => {

    const card = cards[currentIndex];

    if (!card) return;

    if (!unknownCards.includes(currentIndex)) {

      setUnknownCards([
        ...unknownCards,
        currentIndex
      ]);

    }

    setKnownCards(
      knownCards.filter(
        index => index !== currentIndex
      )
    );

    nextCard();
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


  const startRevision = () => {

    const revisionCards = unknownCards.map(
      index => cards[index]
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


  const resetQuiz = () => {

    setCards([]);

    setCurrentIndex(0);

    setFlipped(false);

    setKnownCards([]);

    setUnknownCards([]);

    setRevisionMode(false);
  };


  const completed =
    cards.length > 0 &&
    currentIndex >= cards.length;


  return (

    <div className="flashcards-page">

      <header
        style={{
          background: "#4b35f5",
          color: "white",
          padding: "18px 6%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >

        <h2>🗂️ AI Study Assistant</h2>

        <button
          onClick={() =>
            window.location.href = "/dashboard"
          }
          style={{
            padding: "12px 24px",
            borderRadius: "12px",
            border: "none",
            background: "white",
            color: "#4b35f5",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Dashboard
        </button>

      </header>


      <main
        style={{
          maxWidth: "1000px",
          margin: "40px auto",
          padding: "0 20px"
        }}
      >

        <h1>🗂️ AI Flashcards</h1>

        <p style={{ color: "#64748b", fontSize: "18px" }}>
          Generate flashcards and revise important concepts.
        </p>


        {!cards.length && (

          <div
            style={{
              background: "white",
              padding: "30px",
              borderRadius: "20px",
              marginTop: "30px",
              boxShadow: "0 5px 20px rgba(0,0,0,0.08)"
            }}
          >

            <div
              style={{
                display: "flex",
                gap: "15px",
                marginBottom: "25px"
              }}
            >

              <button
                onClick={() => setMode("topic")}
                style={{
                  flex: 1,
                  padding: "18px",
                  borderRadius: "12px",
                  border:
                    mode === "topic"
                      ? "3px solid #4b35f5"
                      : "1px solid #ddd",
                  background:
                    mode === "topic"
                      ? "#eef0ff"
                      : "white",
                  cursor: "pointer"
                }}
              >
                🤖 Topic Flashcards
              </button>


              <button
                onClick={() => setMode("pdf")}
                style={{
                  flex: 1,
                  padding: "18px",
                  borderRadius: "12px",
                  border:
                    mode === "pdf"
                      ? "3px solid #4b35f5"
                      : "1px solid #ddd",
                  background:
                    mode === "pdf"
                      ? "#eef0ff"
                      : "white",
                  cursor: "pointer"
                }}
              >
                📚 My PDF Flashcards
              </button>

            </div>


            {mode === "topic" && (

              <div>

                <label>Enter Topic</label>

                <input
                  value={topic}
                  onChange={e =>
                    setTopic(e.target.value)
                  }
                  placeholder="Example: Java OOP"
                  style={{
                    width: "100%",
                    padding: "15px",
                    marginTop: "8px",
                    marginBottom: "20px",
                    borderRadius: "10px",
                    border: "1px solid #ccc",
                    fontSize: "16px"
                  }}
                />

              </div>

            )}


            {mode === "pdf" && (

              <div>

                <label>Select PDF</label>

                <select
                  value={documentId}
                  onChange={e =>
                    setDocumentId(e.target.value)
                  }
                  style={{
                    width: "100%",
                    padding: "15px",
                    marginTop: "8px",
                    marginBottom: "20px",
                    borderRadius: "10px",
                    border: "1px solid #ccc"
                  }}
                >

                  <option value="">
                    Select a PDF
                  </option>

                  {pdfs.map(pdf => (

                    <option
                      key={pdf.document_id}
                      value={pdf.document_id}
                    >
                      {pdf.filename}
                    </option>

                  ))}

                </select>


                <label>
                  Topic (optional)
                </label>

                <input
                  value={topic}
                  onChange={e =>
                    setTopic(e.target.value)
                  }
                  placeholder="Example: Newton's Laws"
                  style={{
                    width: "100%",
                    padding: "15px",
                    marginTop: "8px",
                    marginBottom: "20px",
                    borderRadius: "10px",
                    border: "1px solid #ccc"
                  }}
                />

              </div>

            )}


            <label>Number of Flashcards</label>

            <select
              value={questionCount}
              onChange={e =>
                setQuestionCount(e.target.value)
              }
              style={{
                width: "100%",
                padding: "15px",
                marginTop: "8px",
                marginBottom: "25px",
                borderRadius: "10px",
                border: "1px solid #ccc"
              }}
            >

              <option value="5">5</option>
              <option value="10">10</option>
              <option value="15">15</option>
              <option value="20">20</option>

            </select>


            {error && (

              <p
                style={{
                  color: "red",
                  background: "#fff0f0",
                  padding: "12px",
                  borderRadius: "8px"
                }}
              >
                {error}
              </p>

            )}


            <button
              onClick={handleGenerate}
              disabled={loading}
              style={{
                width: "100%",
                padding: "16px",
                background: "#4b35f5",
                color: "white",
                border: "none",
                borderRadius: "12px",
                fontSize: "18px",
                fontWeight: "bold",
                cursor: loading
                  ? "not-allowed"
                  : "pointer"
              }}
            >

              {loading
                ? "Generating Flashcards..."
                : "✨ Generate Flashcards"}

            </button>

          </div>

        )}


        {cards.length > 0 && !completed && (

          <div style={{ marginTop: "30px" }}>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "15px"
              }}
            >

              <strong>
                Card {currentIndex + 1} / {cards.length}
              </strong>

              <span>
                {knownCards.length} Known ·{" "}
                {unknownCards.length} Unknown
              </span>

            </div>


            <div
              onClick={() =>
                setFlipped(!flipped)
              }
              style={{
                minHeight: "350px",
                background:
                  flipped
                    ? "#eef0ff"
                    : "white",
                borderRadius: "25px",
                boxShadow:
                  "0 8px 30px rgba(0,0,0,0.12)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                padding: "40px",
                cursor: "pointer",
                textAlign: "center"
              }}
            >

              {!flipped ? (

                <>
                  <h3>QUESTION</h3>

                  <h2>
                    {cards[currentIndex].question}
                  </h2>

                  <p
                    style={{
                      color: "#64748b",
                      marginTop: "30px"
                    }}
                  >
                    👆 Click to reveal answer
                  </p>
                </>

              ) : (

                <>
                  <h3>ANSWER</h3>

                  <p
                    style={{
                      fontSize: "20px",
                      lineHeight: "1.7"
                    }}
                  >
                    {cards[currentIndex].answer}
                  </p>

                </>

              )}

            </div>


            <div
              style={{
                display: "flex",
                gap: "12px",
                justifyContent: "center",
                marginTop: "25px"
              }}
            >

              <button
                onClick={previousCard}
                disabled={currentIndex === 0}
              >
                ← Previous
              </button>

              <button
                onClick={markUnknown}
                style={{
                  padding: "12px 22px",
                  borderRadius: "10px",
                  border: "none",
                  background: "#fee2e2"
                }}
              >
                ❌ Unknown
              </button>

              <button
                onClick={markKnown}
                style={{
                  padding: "12px 22px",
                  borderRadius: "10px",
                  border: "none",
                  background: "#dcfce7"
                }}
              >
                ✅ Known
              </button>

            </div>

          </div>

        )}


        {completed && (

          <div
            style={{
              marginTop: "40px",
              background: "white",
              padding: "40px",
              borderRadius: "20px",
              textAlign: "center",
              boxShadow:
                "0 8px 30px rgba(0,0,0,0.1)"
            }}
          >

            <h2>🎉 Flashcards Completed!</h2>

            <h3>
              Known: {knownCards.length}
            </h3>

            <h3>
              Unknown: {unknownCards.length}
            </h3>


            <div
              style={{
                margin: "25px 0",
                fontSize: "24px"
              }}
            >

              Progress:{" "}
              {cards.length
                ? Math.round(
                    (knownCards.length /
                      cards.length) *
                      100
                  )
                : 0}
              %

            </div>


            {unknownCards.length > 0 && !revisionMode && (

              <button
                onClick={startRevision}
                style={{
                  padding: "15px 25px",
                  margin: "8px",
                  background: "#4b35f5",
                  color: "white",
                  border: "none",
                  borderRadius: "10px",
                  fontWeight: "bold"
                }}
              >
                🔄 Revise Unknown Cards
              </button>

            )}


            <button
              onClick={resetQuiz}
              style={{
                padding: "15px 25px",
                margin: "8px",
                borderRadius: "10px",
                border: "1px solid #ccc",
                background: "white"
              }}
            >
              Generate New Cards
            </button>

          </div>

        )}

      </main>

    </div>
  );
}
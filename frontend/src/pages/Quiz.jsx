import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getPDFLibrary,
  generateQuiz,
  getQuizHistory,
  deleteQuizHistory,
  deleteAllQuizHistory,
} from "../services/api";

function Quiz() {
  // =====================================================
  // COMMON
  // =====================================================

  const [mode, setMode] = useState("topic");

  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");

  const [questionCount, setQuestionCount] = useState("5");
  const [customCount, setCustomCount] = useState(5);

  const [pdfs, setPdfs] = useState([]);
  const [selectedPDF, setSelectedPDF] = useState("");

  // =====================================================
  // QUIZ
  // =====================================================

  const [questions, setQuestions] = useState([]);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // =====================================================
  // HISTORY
  // =====================================================

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // =====================================================
  // TIMER
  // =====================================================

  const [timeLeft, setTimeLeft] = useState(0);
  const [quizStarted, setQuizStarted] = useState(false);

  // =====================================================
  // LOAD PDFs & HISTORY
  // =====================================================

  useEffect(() => {
    loadPDFs();
    loadQuizHistory();
  }, []);

  const loadPDFs = async () => {
    try {
      setError("");

      const data = await getPDFLibrary();

      setPdfs(data || []);

      if (data && data.length > 0) {
        setSelectedPDF(data[0].document_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const loadQuizHistory = async () => {
    try {
      setHistoryLoading(true);
      const data = await getQuizHistory();
      setHistory(data || []);
    } catch (err) {
      console.error("Failed to load quiz history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleDeleteHistory = async (historyId) => {
    try {
      await deleteQuizHistory(historyId);
      loadQuizHistory();
    } catch (err) {
      setError(err.message || "Failed to delete history item.");
    }
  };

  const handleDeleteAllHistory = async () => {
    try {
      await deleteAllQuizHistory();
      loadQuizHistory();
    } catch (err) {
      setError(err.message || "Failed to clear quiz history.");
    }
  };

  // =====================================================
  // QUESTION COUNT
  // =====================================================

  const getQuestionCount = () => {
    if (questionCount === "custom") {
      return Number(customCount);
    }

    return Number(questionCount);
  };

  // =====================================================
  // TIMER
  // =====================================================

  useEffect(() => {
    if (!quizStarted || submitted || timeLeft <= 0) {
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);

          setSubmitted(true);
          setQuizStarted(false);

          return 0;
        }

        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [quizStarted, submitted, timeLeft]);

  // =====================================================
  // FORMAT TIMER
  // =====================================================

  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    return `${String(minutes).padStart(2, "0")}:${String(
      remainingSeconds
    ).padStart(2, "0")}`;
  };

  // =====================================================
  // GENERATE QUIZ
  // =====================================================

  const handleGenerate = async (e) => {
    e.preventDefault();

    setError("");
    setQuestions([]);
    setSelectedAnswers({});
    setSubmitted(false);
    setQuizStarted(false);
    setTimeLeft(0);

    const count = getQuestionCount();

    // ---------------------------------------------------
    // VALIDATE COUNT
    // ---------------------------------------------------

    if (!Number.isInteger(count) || count < 1 || count > 20) {
      setError("Question number must be between 1 and 20.");
      return;
    }

    // ---------------------------------------------------
    // TOPIC MODE
    // ---------------------------------------------------

    if (mode === "topic" && !topic.trim()) {
      setError("Please enter a topic.");
      return;
    }

    // ---------------------------------------------------
    // PDF MODE
    // ---------------------------------------------------

    if (mode === "pdf" && !selectedPDF) {
      setError("Please select a PDF.");
      return;
    }

    try {
      setLoading(true);

      const data = await generateQuiz({
        mode: mode,

        document_id: mode === "pdf" ? selectedPDF : null,

        topic: topic.trim() || null,

        difficulty: difficulty,

        question_count: count,
      });

      const generatedQuestions = data?.questions || [];

      if (generatedQuestions.length === 0) {
        setError("No questions were generated.");
        return;
      }

      setQuestions(generatedQuestions);

      // Reload history so the new quiz reflects immediately
      loadQuizHistory();

      // -------------------------------------------------
      // TIMER
      // 2 MINUTES PER QUESTION
      // -------------------------------------------------

      const totalTime = generatedQuestions.length * 120;

      setTimeLeft(totalTime);
      setQuizStarted(true);
    } catch (err) {
      setError(err.message || "Failed to generate quiz.");
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // SELECT ANSWER
  // =====================================================

  const handleAnswer = (questionIndex, answer) => {
    if (submitted) {
      return;
    }

    setSelectedAnswers((prev) => ({
      ...prev,
      [questionIndex]: answer,
    }));
  };

  // =====================================================
  // SCORE
  // =====================================================

  const calculateScore = () => {
    let score = 0;

    questions.forEach((question, index) => {
      if (
        selectedAnswers[index] ===
        question.correct_answer
      ) {
        score++;
      }
    });

    return score;
  };

  // =====================================================
  // SUBMIT
  // =====================================================

  const handleSubmit = () => {
    setSubmitted(true);
    setQuizStarted(false);
  };

  // =====================================================
  // RESET
  // =====================================================

  const resetQuiz = () => {
    setQuestions([]);
    setSelectedAnswers({});
    setSubmitted(false);
    setQuizStarted(false);
    setTimeLeft(0);
    setError("");
    loadQuizHistory();
  };

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="min-h-screen bg-gray-100">

      {/* =================================================
          NAVBAR
      ================================================= */}

      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center">

        <h1 className="text-xl font-bold">
          📝 Shaan AI Study Assistant
        </h1>

        <Link
          to="/"
          className="bg-white text-indigo-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </Link>

      </nav>

      {/* =================================================
          MAIN
      ================================================= */}

      <main className="max-w-5xl mx-auto px-6 py-8">

        {/* PAGE HEADER */}

        <div className="mb-8">

          <h2 className="text-3xl font-bold text-gray-800">
            📝 Quiz Generator
          </h2>

          <p className="text-gray-500 mt-2">
            Test your knowledge with Shaan AI generated quizzes.
          </p>

        </div>

        {/* =================================================
            QUIZ SETTINGS
        ================================================= */}

        {questions.length === 0 && (

          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow p-6">

              {/* MODE BUTTONS */}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-7">

                {/* TOPIC MODE */}

                <button
                  type="button"
                  onClick={() => {
                    setMode("topic");
                    setError("");
                  }}
                  className={`p-5 rounded-2xl border-2 text-left transition ${
                    mode === "topic"
                      ? "border-indigo-600 bg-indigo-50"
                      : "border-gray-200 hover:border-indigo-300"
                  }`}
                >

                  <h3 className="text-xl font-bold text-gray-800">
                    🤖 Shaan AI Topic Quiz
                  </h3>

                  <p className="text-gray-500 mt-2">
                    Enter any topic and Shaan AI will generate
                    a quiz using AI knowledge.
                  </p>

                </button>

                {/* PDF MODE */}

                <button
                  type="button"
                  onClick={() => {
                    setMode("pdf");
                    setError("");
                  }}
                  className={`p-5 rounded-2xl border-2 text-left transition ${
                    mode === "pdf"
                      ? "border-indigo-600 bg-indigo-50"
                      : "border-gray-200 hover:border-indigo-300"
                  }`}
                >

                  <h3 className="text-xl font-bold text-gray-800">
                    📚 My PDF Quiz
                  </h3>

                  <p className="text-gray-500 mt-2">
                    Generate questions from your uploaded PDF
                    using Shaan AI.
                  </p>

                </button>

              </div>

              <form onSubmit={handleGenerate}>

                {/* =================================================
                    PDF SELECT
                ================================================= */}

                {mode === "pdf" && (

                  <div className="mb-5">

                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Select PDF
                    </label>

                    <select
                      value={selectedPDF}
                      onChange={(e) =>
                        setSelectedPDF(e.target.value)
                      }
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                    >

                      {pdfs.length === 0 ? (

                        <option value="">
                          No PDFs available
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

                  </div>

                )}

                {/* =================================================
                    TOPIC
                ================================================= */}

                <div className="mb-5">

                  <label className="block text-sm font-semibold text-gray-700 mb-2">

                    {mode === "topic"
                      ? "Enter Topic"
                      : "PDF Topic (Optional)"}

                  </label>

                  <input
                    type="text"
                    value={topic}
                    onChange={(e) =>
                      setTopic(e.target.value)
                    }
                    placeholder={
                      mode === "topic"
                        ? "Example: Java OOP"
                        : "Example: String Class"
                    }
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  />

                  {mode === "pdf" && (

                    <p className="text-sm text-gray-500 mt-2">
                      Leave empty to generate questions from
                      important concepts in the selected PDF.
                    </p>

                  )}

                </div>

                {/* =================================================
                    DIFFICULTY
                ================================================= */}

                <div className="mb-5">

                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Difficulty
                  </label>

                  <select
                    value={difficulty}
                    onChange={(e) =>
                      setDifficulty(e.target.value)
                    }
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  >

                    <option value="easy">
                      Easy
                    </option>

                    <option value="medium">
                      Medium
                    </option>

                    <option value="hard">
                      Hard
                    </option>

                  </select>

                </div>

                {/* =================================================
                    QUESTION COUNT
                ================================================= */}

                <div className="mb-5">

                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Number of Questions
                  </label>

                  <select
                    value={questionCount}
                    onChange={(e) =>
                      setQuestionCount(e.target.value)
                    }
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  >

                    <option value="5">
                      5 Questions
                    </option>

                    <option value="10">
                      10 Questions
                    </option>

                    <option value="15">
                      15 Questions
                    </option>

                    <option value="20">
                      20 Questions
                    </option>

                    <option value="custom">
                      Custom
                    </option>

                  </select>

                </div>

                {/* =================================================
                    CUSTOM COUNT
                ================================================= */}

                {questionCount === "custom" && (

                  <div className="mb-5">

                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Enter Number of Questions
                    </label>

                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={customCount}
                      onChange={(e) =>
                        setCustomCount(e.target.value)
                      }
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                    />

                  </div>

                )}

                {/* =================================================
                    ERROR
                ================================================= */}

                {error && (

                  <div className="mb-5 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl">

                    {error}

                  </div>

                )}

                {/* =================================================
                    GENERATE BUTTON
                ================================================= */}

                <button
                  type="submit"
                  disabled={
                    loading ||
                    (mode === "pdf" && pdfs.length === 0)
                  }
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 rounded-xl transition disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                >

                  {loading
                    ? "🤖 Shaan AI is generating..."
                    : "✨ Generate Quiz"}

                </button>

              </form>

            </div>

            {/* =================================================
                QUIZ HISTORY SECTION
            ================================================= */}

            <div className="bg-white rounded-2xl shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-800">
                  📜 Quiz History
                </h3>
                {history.length > 0 && (
                  <button
                    onClick={handleDeleteAllHistory}
                    className="text-sm text-red-600 hover:text-red-700 font-semibold cursor-pointer"
                  >
                    Clear All History
                  </button>
                )}
              </div>

              {historyLoading ? (
                <p className="text-gray-500 py-4 text-center">Loading history...</p>
              ) : history.length === 0 ? (
                <p className="text-gray-500 py-4 text-center">No past quiz history found.</p>
              ) : (
                <div className="space-y-3">
                  {history.map((item, index) => (
                    <div
                      key={item.id || index}
                      className="border border-gray-200 rounded-xl p-4 flex justify-between items-center bg-gray-50"
                    >
                      <div>
                        <p className="font-semibold text-gray-800">
                          {item.topic || item.filename || "Quiz Session"}
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          Mode: <span className="uppercase">{item.mode}</span> | Difficulty: <span className="capitalize">{item.difficulty}</span> | Questions: {item.question_count}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteHistory(item.id)}
                        className="text-red-500 hover:text-red-700 p-2 cursor-pointer"
                        title="Delete entry"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        )}

        {/* =================================================
            QUIZ HEADER + TIMER
        ================================================= */}

        {questions.length > 0 && (

          <>

            <div className="bg-white rounded-2xl shadow p-5 mb-6 flex justify-between items-center">

              <div>

                <h3 className="text-xl font-bold text-gray-800">

                  {mode === "topic"
                    ? "🤖 Shaan AI Topic Quiz"
                    : "📚 My PDF Quiz"}

                </h3>

                <p className="text-gray-500 mt-1">
                  {questions.length} Questions
                </p>

              </div>

              {/* TIMER */}

              {!submitted && (

                <div
                  className={`px-5 py-3 rounded-xl font-bold text-lg ${
                    timeLeft <= 30
                      ? "bg-red-100 text-red-600"
                      : "bg-indigo-100 text-indigo-600"
                  }`}
                >

                  ⏱️ {formatTime(timeLeft)}

                </div>

              )}

            </div>

            {/* =================================================
                QUESTIONS
            ================================================= */}

            <div className="space-y-6">

              {questions.map((question, index) => (

                <div
                  key={index}
                  className="bg-white rounded-2xl shadow p-6"
                >

                  <h3 className="text-lg font-bold text-gray-800">
                    {index + 1}. {question.question}
                  </h3>

                  {/* OPTIONS */}

                  <div className="mt-5 space-y-3">

                    {question.options.map(
                      (option, optionIndex) => {

                        const isSelected =
                          selectedAnswers[index] === option;

                        const isCorrect =
                          submitted &&
                          option ===
                            question.correct_answer;

                        const isWrong =
                          submitted &&
                          isSelected &&
                          option !==
                            question.correct_answer;

                        return (

                          <button
                            key={optionIndex}
                            type="button"
                            disabled={submitted}
                            onClick={() =>
                              handleAnswer(
                                index,
                                option
                              )
                            }
                            className={`w-full text-left px-4 py-4 rounded-xl border-2 transition flex items-center gap-3 cursor-pointer
                              ${
                                isCorrect
                                  ? "bg-green-50 border-green-500 text-green-700"
                                  : isWrong
                                  ? "bg-red-50 border-red-500 text-red-700"
                                  : isSelected
                                  ? "bg-indigo-50 border-indigo-500 text-indigo-700"
                                  : "border-gray-200 hover:border-indigo-400 hover:bg-indigo-50"
                              }`}
                          >

                            <span
                              className={`w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 font-bold
                                ${
                                  isSelected
                                    ? "bg-indigo-600 border-indigo-600 text-white"
                                    : isCorrect
                                    ? "bg-green-600 border-green-600 text-white"
                                    : "border-gray-300"
                                }`}
                            >

                              {isSelected || isCorrect
                                ? "✓"
                                : String.fromCharCode(
                                    65 + optionIndex
                                  )}

                            </span>

                            <span>
                              {option}
                            </span>

                          </button>

                        );
                      }
                    )}

                  </div>

                  {/* =================================================
                      EXPLANATION
                  ================================================= */}

                  {submitted && (

                    <div className="mt-5 bg-gray-50 rounded-xl p-4">

                      <p className="font-semibold text-gray-800">

                        Correct Answer:{" "}
                        {question.correct_answer}

                      </p>

                      <p className="text-gray-600 mt-2">

                        💡 {question.explanation}

                      </p>

                    </div>

                  )}

                </div>

              ))}

              {/* =================================================
                  SUBMIT / RESULT
              ================================================= */}

              {!submitted ? (

                <button
                  onClick={handleSubmit}
                  disabled={
                    Object.keys(selectedAnswers).length !==
                    questions.length
                  }
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-4 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >

                  ✅ Submit Quiz

                </button>

              ) : (

                <div className="bg-white rounded-2xl shadow p-7 text-center">

                  <h3 className="text-3xl font-bold text-gray-800">
                    🎉 Quiz Completed!
                  </h3>

                  <p className="text-2xl text-indigo-600 font-bold mt-4">

                    Score: {calculateScore()} /{" "}
                    {questions.length}

                  </p>

                  <p className="text-gray-500 mt-2">

                    {Math.round(
                      (calculateScore() /
                        questions.length) *
                        100
                    )}
                    % Accuracy

                  </p>

                  <button
                    onClick={resetQuiz}
                    className="mt-6 bg-indigo-600 hover:bg-indigo-700 text-white px-7 py-3 rounded-xl font-semibold cursor-pointer"
                  >

                    🔄 Generate Another Quiz

                  </button>

                </div>

              )}

            </div>

          </>

        )}

      </main>

    </div>
  );
}

export default Quiz;
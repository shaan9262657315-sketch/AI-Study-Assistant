import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPDFLibrary, generateStudyGuide, apiFetch } from "../services/api";

function StudyGuide() {
  const [pdfs, setPdfs] = useState([]);
  const [selectedPDF, setSelectedPDF] = useState("");

  const [language, setLanguage] = useState("english");
  const [questionCount, setQuestionCount] = useState("5");

  const [summary, setSummary] = useState("");
  const [questions, setQuestions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // History & Library States
  const [historyList, setHistoryList] = useState([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState("");

  // =====================================================
  // LOAD PDF LIBRARY & STUDY GUIDE HISTORY
  // =====================================================

  useEffect(() => {
    loadPDFs();
    loadHistory();
  }, []);

  const loadPDFs = async () => {
    try {
      const data = await getPDFLibrary();
      setPdfs(data);
      if (data.length > 0 && !selectedPDF) {
        setSelectedPDF(data[0].document_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await apiFetch("/study-guide/library");
      setHistoryList(data || []);
    } catch (err) {
      console.error("Failed to load study guide history", err);
    }
  };

  // =====================================================
  // SELECT SAVED HISTORY ITEM
  // =====================================================

  const handleSelectHistory = (id) => {
    setSelectedHistoryId(id);
    if (!id) {
      setSummary("");
      setQuestions([]);
      return;
    }

    const found = historyList.find((item) => item.id === Number(id));
    if (found) {
      setSummary(found.summary || "");
      
      // Handle both JSON string or parsed array formats for questions
      let parsedQuestions = found.important_questions;
      if (typeof parsedQuestions === "string") {
        try {
          parsedQuestions = JSON.parse(parsedQuestions);
        } catch {
          parsedQuestions = [];
        }
      }
      setQuestions(parsedQuestions || []);
      setLanguage(found.language || "english");
      if (found.document_id) {
        setSelectedPDF(found.document_id);
      }
    }
  };

  // =====================================================
  // DELETE INDIVIDUAL STUDY GUIDE HISTORY ITEM
  // =====================================================

  const handleDeleteHistory = async (id) => {
    if (!window.confirm("Are you sure you want to delete this study guide?")) return;
    try {
      await apiFetch(`/study-guide/library/${id}`, {
        method: "DELETE",
      });
      
      // Update history list state by removing the deleted item
      setHistoryList((prev) => prev.filter((item) => item.id !== Number(id)));
      
      // If the currently viewed item was deleted, clear the view
      if (selectedHistoryId === String(id) || selectedHistoryId === Number(id)) {
        setSelectedHistoryId("");
        setSummary("");
        setQuestions([]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  // =====================================================
  // GENERATE STUDY GUIDE
  // =====================================================

  const handleGenerate = async () => {
    if (!selectedPDF) {
      setError("Please select a PDF.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSummary("");
      setQuestions([]);
      setSelectedHistoryId("");

      const data = await generateStudyGuide({
        document_id: selectedPDF,
        question_count: Number(questionCount),
        language: language,
      });

      setSummary(data.summary || "");
      setQuestions(data.important_questions || []);
      
      // Refresh history list after generating a new one
      await loadHistory();
      if (data.id) {
        setSelectedHistoryId(data.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
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
          📚 Shaan AI Study Assistant
        </h1>

        <Link
          to="/"
          className="bg-white text-indigo-600 px-6 py-3 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </Link>
      </nav>

      {/* =================================================
          MAIN
      ================================================= */}

      <main className="max-w-5xl mx-auto px-6 py-10">

        {/* Heading */}

        <div className="mb-8">
          <h2 className="text-4xl font-bold text-gray-900">
            📚 Study Guide
          </h2>
          <p className="text-xl text-gray-500 mt-3">
            Generate a complete study guide from your PDF using Shaan AI.
          </p>
        </div>

        {/* =================================================
            SAVED HISTORY SELECTOR
        ================================================= */}

        {historyList.length > 0 && (
          <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-6 mb-8">
            <label className="block text-lg font-semibold text-gray-800 mb-3">
              📖 Saved Study Guide History
            </label>
            <div className="flex gap-4 items-center">
              <select
                value={selectedHistoryId}
                onChange={(e) => handleSelectHistory(e.target.value)}
                className="w-full px-5 py-3 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 transition"
              >
                <option value="">-- Select from saved history --</option>
                {historyList.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.filename} ({item.language}) - {new Date(item.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>

              {selectedHistoryId && (
                <button
                  onClick={() => handleDeleteHistory(selectedHistoryId)}
                  className="bg-red-500 hover:bg-red-600 text-white px-5 py-3 rounded-2xl font-semibold transition whitespace-nowrap"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        )}

        {/* =================================================
            GENERATOR CARD
        ================================================= */}

        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">

          {/* PDF */}

          <label className="block text-lg font-semibold text-gray-800 mb-3">
            Select PDF
          </label>

          <select
            value={selectedPDF}
            onChange={(e) => setSelectedPDF(e.target.value)}
            className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 transition"
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

          {/* =================================================
              LANGUAGE
          ================================================= */}

          <label className="block text-lg font-semibold text-gray-800 mt-6 mb-3">
            Language
          </label>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 transition"
          >
            <option value="english">
              🇬🇧 English
            </option>
            <option value="hinglish">
              🇮🇳 Hinglish
            </option>
          </select>

          {/* =================================================
              QUESTION COUNT
          ================================================= */}

          <label className="block text-lg font-semibold text-gray-800 mt-6 mb-3">
            Number of Important Questions
          </label>

          <select
            value={questionCount}
            onChange={(e) => setQuestionCount(e.target.value)}
            className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 transition"
          >
            <option value="5">5 Questions</option>
            <option value="10">10 Questions</option>
            <option value="15">15 Questions</option>
            <option value="20">20 Questions</option>
          </select>

          {/* =================================================
              ERROR
          ================================================= */}

          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl text-lg">
              {error}
            </div>
          )}

          {/* =================================================
              GENERATE BUTTON
          ================================================= */}

          <button
            onClick={handleGenerate}
            disabled={loading || !selectedPDF}
            className="w-full mt-7 bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-4 rounded-2xl transition disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading
              ? "🤖 Shaan AI is generating..."
              : "✨ Generate Study Guide"
            }
          </button>

        </div>

        {/* =================================================
            SUMMARY
        ================================================= */}

        {summary && (
          <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8 mt-8">
            <h3 className="text-3xl font-bold text-gray-900 mb-5">
              📝 PDF Summary
            </h3>
            <div className="text-gray-700 text-lg leading-8 whitespace-pre-wrap">
              {summary}
            </div>
          </div>
        )}

        {/* =================================================
            IMPORTANT QUESTIONS
        ================================================= */}

        {questions.length > 0 && (
          <div className="mt-8">
            <h3 className="text-3xl font-bold text-gray-900 mb-6">
              ⭐ Important Questions
            </h3>

            <div className="space-y-6">
              {questions.comap ? null : questions.map((item, index) => (
                <div
                  key={index}
                  className="bg-white rounded-3xl shadow-md border border-gray-200 p-7"
                >
                  <h4 className="text-xl font-bold text-gray-900">
                    Q{index + 1}. {item.question}
                  </h4>

                  <div className="mt-5 bg-indigo-50 border border-indigo-100 rounded-2xl p-5">
                    <h5 className="text-lg font-bold text-indigo-700 mb-2">
                      💡 Solution
                    </h5>
                    <p className="text-gray-700 text-lg leading-8 whitespace-pre-wrap">
                      {item.answer}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default StudyGuide;
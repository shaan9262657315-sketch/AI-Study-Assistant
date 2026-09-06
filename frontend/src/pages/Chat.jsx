import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  askChatQuestion,
  getChatHistory,
  deleteChatHistory,
  deleteAllChatHistory,
} from "../services/api";

function Chat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // =====================================================
  // CHAT HISTORY
  // =====================================================

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // =====================================================
  // LOAD CHAT HISTORY
  // =====================================================

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await getChatHistory();

        setHistory(data);
      } catch (err) {
        console.error("History Error:", err);
      } finally {
        setHistoryLoading(false);
      }
    };

    loadHistory();
  }, []);

  // =====================================================
  // ASK QUESTION
  // =====================================================

  const handleAsk = async (e) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const data = await askChatQuestion(question);

      setAnswer(data.answer);

      // -------------------------------------------------
      // ADD NEW CHAT TO HISTORY
      // -------------------------------------------------

      setHistory((prev) => [
        {
          id: data.id,
          question: question.trim(),
          answer: data.answer,
          created_at: data.created_at,
        },
        ...prev,
      ]);

      // Clear question box after successful request
      setQuestion("");

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // DELETE ONE CHAT
  // =====================================================

  const handleDelete = async (historyId) => {
    try {
      await deleteChatHistory(historyId);

      setHistory((prev) =>
        prev.filter((item) => item.id !== historyId)
      );

    } catch (err) {
      setError(err.message);
    }
  };

  // =====================================================
  // DELETE ALL CHAT HISTORY
  // =====================================================

  const handleDeleteAll = async () => {
    try {
      await deleteAllChatHistory();

      setHistory([]);

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">

      {/* Navbar */}
      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">
          🤖 Shaan AI — Study Assistant
        </h1>

        <Link
          to="/"
          className="bg-white text-indigo-600 px-6 py-3 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </Link>
      </nav>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-12">

        <div className="mb-10">
          <h2 className="text-5xl font-bold text-gray-900 flex items-center gap-4">
            🤖 AI Chat
          </h2>

          <p className="text-xl text-gray-500 mt-4">
            Ask anything and get an answer from Shaan AI.
          </p>
        </div>

        {/* Question Box */}
        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">

          <form onSubmit={handleAsk}>

            <label className="block text-lg font-semibold text-gray-800 mb-3">
              Your Question
            </label>

            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything..."
              rows="7"
              className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-2xl outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 resize-none transition"
            />

            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-4 rounded-2xl transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "🤖 Thinking..." : "✨ Ask AI"}
            </button>

          </form>

          {/* Error */}
          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl">
              {error}
            </div>
          )}

          {/* Answer */}
          {answer && (
            <div className="mt-8 bg-indigo-50 border border-indigo-100 rounded-2xl p-6">

              <h3 className="text-2xl font-bold text-indigo-700 mb-4">
                🤖 AI Answer
              </h3>

              <div className="text-gray-800 text-lg leading-8 whitespace-pre-wrap">
                {answer}
              </div>

            </div>
          )}

        </div>

        {/* =================================================
            CHAT HISTORY
        ================================================= */}

        <div className="mt-12">

          <div className="flex justify-between items-center mb-6">

            <h2 className="text-3xl font-bold text-gray-900">
              📚 Chat History
            </h2>

            {history.length > 0 && (
              <button
                onClick={handleDeleteAll}
                className="bg-red-500 hover:bg-red-600 text-white px-5 py-3 rounded-xl font-semibold transition"
              >
                🗑️ Delete All
              </button>
            )}

          </div>

          {/* Loading */}
          {historyLoading ? (

            <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-6 text-gray-500 text-lg">
              Loading chat history...
            </div>

          ) : history.length === 0 ? (

            <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-6 text-gray-500 text-lg">
              No chat history yet.
            </div>

          ) : (

            <div className="space-y-6">

              {history.map((item) => (

                <div
                  key={item.id}
                  className="bg-white rounded-2xl shadow-md border border-gray-200 p-6"
                >

                  {/* Question */}
                  <div className="mb-4">

                    <div className="flex justify-between items-start gap-4">

                      <h3 className="text-lg font-bold text-gray-900 mb-2">
                        🧑‍🎓 Question
                      </h3>

                      <button
                        onClick={() => handleDelete(item.id)}
                        className="text-red-500 hover:text-red-700 font-semibold text-sm"
                      >
                        🗑️ Delete
                      </button>

                    </div>

                    <p className="text-gray-700 text-lg">
                      {item.question}
                    </p>

                  </div>

                  {/* Answer */}
                  <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">

                    <h3 className="text-lg font-bold text-indigo-700 mb-2">
                      🤖 AI Answer
                    </h3>

                    <p className="text-gray-800 leading-7 whitespace-pre-wrap">
                      {item.answer}
                    </p>

                  </div>

                  {/* Date */}
                  {item.created_at && (
                    <p className="text-sm text-gray-400 mt-4">
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  )}

                </div>

              ))}

            </div>

          )}

        </div>

      </main>
    </div>
  );
}

export default Chat;
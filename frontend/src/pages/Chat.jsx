import { useState } from "react";
import { Link } from "react-router-dom";
import { askChatQuestion } from "../services/api";

function Chat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAsk = async (e) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const data = await askChatQuestion(question);
      setAnswer(data.answer);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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

      </main>
    </div>
  );
}

export default Chat;
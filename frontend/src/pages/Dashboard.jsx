import { Link, useNavigate } from "react-router-dom";
import { clearToken } from "../services/api";

function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearToken();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-100">

      {/* Navbar */}
      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center">

        {/* Brand */}
        <div>
          <h1 className="text-xl font-bold">
            📚 AI Study Assistant
          </h1>

          <p className="text-xs text-indigo-100 mt-1 ml-7">
  ✦ Built by 𝓢𝓱𝓪𝓪𝓷 𝓔 𝓢𝓪𝓱𝓲𝓵 ✦
</p>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="bg-white text-indigo-600 px-6 py-3 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Logout
        </button>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-10">

        {/* Welcome Section */}
        <div className="mb-10">
          <h2 className="text-4xl font-bold text-gray-900">
            Welcome to Dashboard 🎓
          </h2>

          <p className="text-gray-500 text-xl mt-3">
            Your AI Study Assistant is ready!
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

          {/* PDF Library */}
          <Link
            to="/library"
            className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition"
          >
            <h3 className="text-2xl font-bold text-gray-900">
              📄 PDF Library
            </h3>

            <p className="text-gray-500 text-lg mt-3">
              Upload and study your PDFs.
            </p>
          </Link>

          {/* AI Chat */}
          <Link
            to="/chat"
            className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition"
          >
            <h3 className="text-2xl font-bold text-gray-900">
              🤖 AI Chat
            </h3>

            <p className="text-gray-500 text-lg mt-3">
  Ask anything and get answers from Shaan AI.
</p>
          </Link>

          {/* Flashcards */}
          <Link
            to="/flashcards"
            className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition"
          >
            <h3 className="text-2xl font-bold text-gray-900">
              📁 AI Flashcards
            </h3>

            <p className="text-gray-500 text-lg mt-3">
              Generate AI flashcards and revise important concepts.
            </p>
          </Link>

          {/* Quiz */}
          <Link
            to="/quiz"
            className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition"
          >
            <h3 className="text-2xl font-bold text-gray-900">
              📝 Quiz
            </h3>

            <p className="text-gray-500 text-lg mt-3">
              Generate AI quizzes from topics or your PDFs.
            </p>
          </Link>

          {/* Study Guide */}
          <Link
            to="/study-guide"
            className="bg-white p-8 rounded-2xl shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition md:col-span-2"
          >
            <h3 className="text-2xl font-bold text-gray-900">
              📚 Study Guide
            </h3>

            <p className="text-gray-500 text-lg mt-3">
              Get PDF summary, important questions and detailed solutions.
            </p>
          </Link>

        </div>
      </main>
    </div>
  );
}

export default Dashboard;
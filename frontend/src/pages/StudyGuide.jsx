import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPDFLibrary, generateStudyGuide } from "../services/api";

function StudyGuide() {
  const [pdfs, setPdfs] = useState([]);
  const [selectedPDF, setSelectedPDF] = useState("");
  const [language, setLanguage] = useState("english");
  const [questionCount, setQuestionCount] = useState(5);

  const [summary, setSummary] = useState("");
  const [questions, setQuestions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadPDFs();
  }, []);

  const loadPDFs = async () => {
    try {
      const data = await getPDFLibrary();

      setPdfs(data);

      if (data.length > 0) {
        setSelectedPDF(data[0].document_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGenerate = async () => {
    if (!selectedPDF) {
      setError("Please select a PDF.");
      return;
    }

    setLoading(true);
    setError("");
    setSummary("");
    setQuestions([]);

    try {
      const data = await generateStudyGuide({
        document_id: selectedPDF,
        question_count: Number(questionCount),
        language: language
      });

      setSummary(data.summary);
      setQuestions(data.important_questions);
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
          📚 AI Study Assistant
        </h1>

        <Link
          to="/"
          className="bg-white text-indigo-600 px-6 py-3 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </Link>

      </nav>


      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-10">

        {/* Heading */}
        <div className="mb-8">

          <h2 className="text-4xl font-bold text-gray-900">
            📚 Study Guide
          </h2>

          <p className="text-xl text-gray-500 mt-3">
            Get a summary, important questions and solutions from your PDF.
          </p>

        </div>


        {/* Generator Card */}
        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">

          {/* Select PDF */}
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


          {/* Language */}
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


          {/* Number of Questions */}
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


          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !selectedPDF}
            className="w-full mt-7 bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-semibold py-4 rounded-2xl transition disabled:opacity-60 disabled:cursor-not-allowed"
          >

            {loading
              ? "🤖 Generating Study Guide..."
              : "✨ Generate Study Guide"
            }

          </button>


          {/* Error */}
          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl text-lg">
              {error}
            </div>
          )}

        </div>


        {/* Summary */}
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


        {/* Important Questions */}
        {questions.length > 0 && (

          <div className="mt-8">

            <h3 className="text-3xl font-bold text-gray-900 mb-6">
              ⭐ Important Questions
            </h3>

            <div className="space-y-6">

              {questions.map((item, index) => (

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
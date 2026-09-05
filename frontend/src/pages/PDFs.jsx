import { useEffect, useState } from "react";
import {
  uploadPDF,
  getPDFLibrary,
  deletePDF,
  reloadPDFs,
  askPDFQuestion,
} from "../services/api";

export default function PDFs() {
  // =====================================================
  // PDF STATE
  // =====================================================

  const [pdfs, setPdfs] = useState([]);

  const [selectedFile, setSelectedFile] = useState(null);

  const [loading, setLoading] = useState(false);

  const [libraryLoading, setLibraryLoading] = useState(false);

  const [deletingId, setDeletingId] = useState("");

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");


  // =====================================================
  // ASK PDF QUESTION
  // =====================================================

  const [question, setQuestion] = useState("");

  const [answer, setAnswer] = useState("");

  const [asking, setAsking] = useState(false);


  // =====================================================
  // LOAD PDF LIBRARY
  // =====================================================

  useEffect(() => {
    loadPDFs();
  }, []);


  const loadPDFs = async () => {
    try {
      setLibraryLoading(true);
      setError("");

      const data = await getPDFLibrary();

      setPdfs(data || []);
    } catch (err) {
      setError(err.message || "Could not load PDF library.");
    } finally {
      setLibraryLoading(false);
    }
  };


  // =====================================================
  // FILE SELECT
  // =====================================================

  const handleFileChange = (e) => {
    setError("");
    setSuccess("");

    const file = e.target.files?.[0];

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (file.type !== "application/pdf") {
      setError("Only PDF files are allowed.");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }

    setSelectedFile(file);
  };


  // =====================================================
  // UPLOAD PDF
  // =====================================================

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please select a PDF first.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");

      const data = await uploadPDF(selectedFile);

      setSuccess(
        data.message || "PDF uploaded successfully."
      );

      setSelectedFile(null);

      // Reset file input
      const fileInput = document.getElementById(
        "pdf-upload"
      );

      if (fileInput) {
        fileInput.value = "";
      }

      // Reload library
      await loadPDFs();

    } catch (err) {
      setError(
        err.message || "PDF upload failed."
      );
    } finally {
      setLoading(false);
    }
  };


  // =====================================================
  // DELETE PDF
  // =====================================================

  const handleDelete = async (documentId, filename) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${filename}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(documentId);
      setError("");
      setSuccess("");

      const data = await deletePDF(documentId);

      setSuccess(
        data.message || "PDF deleted successfully."
      );

      // Remove from UI immediately
      setPdfs((prev) =>
        prev.filter(
          (pdf) =>
            pdf.document_id !== documentId
        )
      );

      // Clear answer if needed
      setAnswer("");

    } catch (err) {
      setError(
        err.message || "Could not delete PDF."
      );
    } finally {
      setDeletingId("");
    }
  };


  // =====================================================
  // RELOAD PDF LIBRARY
  // =====================================================

  const handleReload = async () => {
    try {
      setLibraryLoading(true);
      setError("");
      setSuccess("");

      await reloadPDFs();

      await loadPDFs();

      setSuccess(
        "PDF library reloaded successfully."
      );

    } catch (err) {
      setError(
        err.message || "Could not reload PDF library."
      );
    } finally {
      setLibraryLoading(false);
    }
  };


  // =====================================================
  // ASK PDF QUESTION
  // =====================================================

  const handleAskQuestion = async () => {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    if (pdfs.length === 0) {
      setError("Please upload a PDF first.");
      return;
    }

    try {
      setAsking(true);
      setError("");
      setAnswer("");

      const data = await askPDFQuestion({
        question: question.trim(),

        mode: "pdf",

        language: "english",

        selected_documents: pdfs.map(
          (pdf) => pdf.document_id
        ),

        top_k: 5,
      });

      setAnswer(
        data.answer ||
        data.response ||
        data.result ||
        "No answer received."
      );

    } catch (err) {
      setError(
        err.message || "Could not get an answer."
      );
    } finally {
      setAsking(false);
    }
  };


  // =====================================================
  // FORMAT DATE
  // =====================================================

  const formatDate = (date) => {
    if (!date) {
      return "Unknown";
    }

    try {
      return new Date(date).toLocaleString();
    } catch {
      return "Unknown";
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

      <nav className="bg-indigo-600 text-white px-6 py-4 flex justify-between items-center shadow">

        <h1 className="text-xl font-bold">
          📚 AI Study Assistant
        </h1>

        <button
          onClick={() => {
            window.location.href = "/";
          }}
          className="bg-white text-indigo-600 px-5 py-2.5 rounded-xl font-semibold hover:bg-gray-100 transition"
        >
          Dashboard
        </button>

      </nav>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="max-w-6xl mx-auto px-6 py-10">

        {/* PAGE HEADER */}

        <div className="mb-8">

          <h2 className="text-4xl font-bold text-gray-900">
            📚 PDF Library
          </h2>

          <p className="text-lg text-gray-500 mt-2">
            Upload your study PDFs and ask AI questions
            directly from your documents.
          </p>

        </div>


        {/* =================================================
            ERROR
        ================================================= */}

        {error && (

          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-5 py-4 rounded-xl">

            ❌ {error}

          </div>

        )}


        {/* =================================================
            SUCCESS
        ================================================= */}

        {success && (

          <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-5 py-4 rounded-xl">

            ✅ {success}

          </div>

        )}


        {/* =================================================
            UPLOAD CARD
        ================================================= */}

        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8 mb-8">

          <div className="flex items-center gap-3 mb-6">

            <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center text-2xl">
              📤
            </div>

            <div>

              <h3 className="text-2xl font-bold text-gray-900">
                Upload Study PDF
              </h3>

              <p className="text-gray-500">
                Upload a PDF to add it to your AI study library.
              </p>

            </div>

          </div>


          {/* FILE INPUT */}

          <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center hover:border-indigo-400 transition">

            <input
              id="pdf-upload"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />

            <label
              htmlFor="pdf-upload"
              className="cursor-pointer"
            >

              <div className="text-5xl mb-4">
                📄
              </div>

              <p className="text-lg font-semibold text-gray-800">
                Click to select a PDF
              </p>

              <p className="text-gray-500 mt-1">
                Only PDF files are supported
              </p>

            </label>


            {/* SELECTED FILE */}

            {selectedFile && (

              <div className="mt-6 bg-indigo-50 border border-indigo-100 rounded-xl p-4">

                <p className="font-semibold text-indigo-700">
                  📄 {selectedFile.name}
                </p>

                <p className="text-sm text-gray-500 mt-1">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>

              </div>

            )}

          </div>


          {/* UPLOAD BUTTON */}

          <button
            onClick={handleUpload}
            disabled={loading || !selectedFile}
            className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 rounded-xl transition disabled:opacity-60 disabled:cursor-not-allowed"
          >

            {loading
              ? "🤖 Uploading & Indexing..."
              : "📤 Upload PDF"
            }

          </button>

        </div>


        {/* =================================================
            PDF LIBRARY
        ================================================= */}

        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8 mb-8">

          <div className="flex justify-between items-center mb-6">

            <div>

              <h3 className="text-2xl font-bold text-gray-900">
                📚 My PDFs
              </h3>

              <p className="text-gray-500 mt-1">
                {pdfs.length} PDF
                {pdfs.length !== 1 ? "s" : ""} in your library
              </p>

            </div>


            <button
              onClick={handleReload}
              disabled={libraryLoading}
              className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold transition disabled:opacity-60"
            >

              {libraryLoading
                ? "⏳ Reloading..."
                : "🔄 Reload"
              }

            </button>

          </div>


          {/* LOADING */}

          {libraryLoading && (

            <div className="text-center py-10 text-gray-500">
              Loading PDF library...
            </div>

          )}


          {/* EMPTY */}

          {!libraryLoading && pdfs.length === 0 && (

            <div className="text-center py-12">

              <div className="text-6xl mb-4">
                📂
              </div>

              <h4 className="text-xl font-bold text-gray-800">
                No PDFs yet
              </h4>

              <p className="text-gray-500 mt-2">
                Upload your first study PDF to get started.
              </p>

            </div>

          )}


          {/* PDF LIST */}

          {!libraryLoading && pdfs.length > 0 && (

            <div className="space-y-4">

              {pdfs.map((pdf) => (

                <div
                  key={pdf.document_id}
                  className="border border-gray-200 rounded-2xl p-5 hover:border-indigo-300 hover:shadow-sm transition"
                >

                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

                    {/* PDF INFO */}

                    <div className="flex items-center gap-4">

                      <div className="w-14 h-14 bg-red-50 rounded-xl flex items-center justify-center text-2xl">
                        📕
                      </div>

                      <div>

                        <h4 className="font-bold text-gray-900 text-lg">
                          {pdf.filename}
                        </h4>

                        <div className="flex flex-wrap gap-3 text-sm text-gray-500 mt-1">

                          <span>
                            📄 {pdf.page_count || 0} pages
                          </span>

                          <span>
                            🕒 {formatDate(pdf.uploaded_at)}
                          </span>

                        </div>

                      </div>

                    </div>


                    {/* DELETE */}

                    <button
                      onClick={() =>
                        handleDelete(
                          pdf.document_id,
                          pdf.filename
                        )
                      }
                      disabled={
                        deletingId ===
                        pdf.document_id
                      }
                      className="px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-xl font-semibold transition disabled:opacity-60"
                    >

                      {deletingId === pdf.document_id
                        ? "Deleting..."
                        : "🗑️ Delete"
                      }

                    </button>

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>


        {/* =================================================
            ASK PDF AI
        ================================================= */}

        <div className="bg-white rounded-3xl shadow-md border border-gray-200 p-8">

          <div className="flex items-center gap-3 mb-6">

            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center text-2xl">
              🤖
            </div>

            <div>

              <h3 className="text-2xl font-bold text-gray-900">
                Ask AI About Your PDFs
              </h3>

              <p className="text-gray-500">
                Ask questions and get answers using your uploaded PDFs.
              </p>

            </div>

          </div>


          {/* QUESTION INPUT */}

          <textarea
            value={question}
            onChange={(e) => {
              setQuestion(e.target.value);
              setError("");
            }}
            placeholder="Example: Explain Newton's laws mentioned in the PDF."
            rows={4}
            className="w-full px-5 py-4 border-2 border-gray-300 rounded-2xl outline-none resize-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 transition"
          />


          {/* ASK BUTTON */}

          <button
            onClick={handleAskQuestion}
            disabled={
              asking ||
              !question.trim() ||
              pdfs.length === 0
            }
            className="w-full mt-5 bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 rounded-xl transition disabled:opacity-60 disabled:cursor-not-allowed"
          >

            {asking
              ? "🤖 AI is thinking..."
              : "✨ Ask AI"
            }

          </button>


          {/* ANSWER */}

          {answer && (

            <div className="mt-7 bg-indigo-50 border border-indigo-100 rounded-2xl p-6">

              <div className="flex items-center gap-2 mb-3">

                <span className="text-2xl">
                  🤖
                </span>

                <h4 className="text-xl font-bold text-indigo-700">
                  AI Answer
                </h4>

              </div>

              <div className="text-gray-700 leading-8 whitespace-pre-wrap">
                {answer}
              </div>

            </div>

          )}

        </div>

      </main>

    </div>
  );
}
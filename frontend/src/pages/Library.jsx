import { useEffect, useState } from "react";

import {
  getPDFLibrary,
  uploadPDF,
  deletePDF
} from "../services/api";


function Library() {

  const [pdfs, setPdfs] = useState([]);

  const [selectedFile, setSelectedFile] = useState(null);

  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState(false);

  const [deleting, setDeleting] = useState(null);

  const [message, setMessage] = useState("");

  const [error, setError] = useState("");


  // =========================================================
  // LOAD PDF LIBRARY
  // =========================================================

  const loadPDFs = async () => {

    try {

      setLoading(true);

      setError("");

      const data = await getPDFLibrary();

      setPdfs(data);

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }

  };


  // =========================================================
  // LOAD PDFs ON PAGE OPEN
  // =========================================================

  useEffect(() => {

    loadPDFs();

  }, []);


  // =========================================================
  // UPLOAD PDF
  // =========================================================

  const handleUpload = async (e) => {

    e.preventDefault();


    // -------------------------------------------------------
    // CHECK FILE
    // -------------------------------------------------------

    if (!selectedFile) {

      setError("Please select a PDF file.");

      return;

    }


    // -------------------------------------------------------
    // CHECK PDF TYPE
    // -------------------------------------------------------

    if (selectedFile.type !== "application/pdf") {

      setError("Only PDF files are allowed.");

      return;

    }


    try {

      setUploading(true);

      setError("");

      setMessage("");


      // -----------------------------------------------------
      // UPLOAD
      // -----------------------------------------------------

      await uploadPDF(selectedFile);


      setMessage(
        "PDF uploaded successfully! 🎉"
      );


      setSelectedFile(null);


      // -----------------------------------------------------
      // RESET FILE INPUT
      // -----------------------------------------------------

      e.target.reset();


      // -----------------------------------------------------
      // RELOAD LIBRARY
      // -----------------------------------------------------

      await loadPDFs();

    } catch (err) {

      setError(err.message);

    } finally {

      setUploading(false);

    }

  };


  // =========================================================
  // DELETE PDF
  // =========================================================

  const handleDelete = async (
    documentId,
    filename
  ) => {

    // -------------------------------------------------------
    // CONFIRM DELETE
    // -------------------------------------------------------

    const confirmed = window.confirm(
      `Are you sure you want to delete "${filename}"?`
    );


    if (!confirmed) {

      return;

    }


    try {

      setDeleting(documentId);

      setError("");

      setMessage("");


      // -----------------------------------------------------
      // DELETE PDF
      // -----------------------------------------------------

      await deletePDF(documentId);


      setMessage(
        "PDF deleted successfully."
      );


      // -----------------------------------------------------
      // RELOAD LIBRARY
      // -----------------------------------------------------

      await loadPDFs();

    } catch (err) {

      setError(err.message);

    } finally {

      setDeleting(null);

    }

  };


  // =========================================================
  // UI
  // =========================================================

  return (

    <div className="min-h-screen bg-gray-100">


      {/* =====================================================
          NAVBAR
      ===================================================== */}

      <nav className="bg-indigo-600 text-white px-6 py-4 flex items-center justify-between">

        <h1 className="text-xl font-bold">
          📚 AI Study Assistant
        </h1>


        <a
          href="/"
          className="bg-white text-indigo-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100"
        >
          Dashboard
        </a>

      </nav>


      {/* =====================================================
          MAIN
      ===================================================== */}

      <main className="max-w-6xl mx-auto px-6 py-8">


        {/* ===================================================
            PAGE HEADING
        =================================================== */}

        <div className="mb-8">

          <h2 className="text-3xl font-bold text-gray-800">
            📄 PDF Library
          </h2>


          <p className="text-gray-500 mt-2">
            Upload and manage your study PDFs.
          </p>

        </div>


        {/* ===================================================
            UPLOAD BOX
        =================================================== */}

        <div className="bg-white rounded-2xl shadow p-6 mb-8">


          <h3 className="text-xl font-bold text-gray-800 mb-4">
            📤 Upload New PDF
          </h3>


          <form onSubmit={handleUpload}>


            {/* ------------------------------------------------
                FILE SELECT AREA
            ------------------------------------------------ */}

            <div
              className="
                border-2
                border-dashed
                border-gray-300
                rounded-xl
                p-8
                text-center
                hover:border-indigo-400
                transition
              "
            >


              <div className="text-5xl mb-4">
                📄
              </div>


              <p className="text-gray-600 mb-4">
                Select a PDF file to upload
              </p>


              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => {

                  setSelectedFile(
                    e.target.files[0]
                  );

                  setError("");

                  setMessage("");

                }}
                className="
                  block
                  w-full
                  max-w-md
                  mx-auto
                  text-sm
                  text-gray-600

                  file:mr-4
                  file:py-2
                  file:px-4

                  file:rounded-lg
                  file:border-0

                  file:bg-indigo-50
                  file:text-indigo-700

                  file:font-semibold

                  hover:file:bg-indigo-100
                "
              />


              {/* ------------------------------------------------
                  SELECTED FILE
              ------------------------------------------------ */}

              {selectedFile && (

                <p className="mt-4 text-sm text-gray-600">

                  Selected:

                  {" "}

                  <b>
                    {selectedFile.name}
                  </b>

                </p>

              )}

            </div>


            {/* ------------------------------------------------
                UPLOAD BUTTON
            ------------------------------------------------ */}

            <button
              type="submit"
              disabled={uploading}
              className="
                mt-5
                w-full
                bg-indigo-600
                hover:bg-indigo-700
                text-white
                font-semibold
                py-3
                rounded-xl
                transition

                disabled:opacity-60
                disabled:cursor-not-allowed
              "
            >

              {uploading
                ? "Uploading..."
                : "Upload PDF"
              }

            </button>


          </form>


          {/* =================================================
              SUCCESS MESSAGE
          ================================================= */}

          {message && (

            <div
              className="
                mt-4
                bg-green-50
                border
                border-green-200
                text-green-700
                px-4
                py-3
                rounded-xl
              "
            >
              {message}
            </div>

          )}


          {/* =================================================
              ERROR MESSAGE
          ================================================= */}

          {error && (

            <div
              className="
                mt-4
                bg-red-50
                border
                border-red-200
                text-red-600
                px-4
                py-3
                rounded-xl
              "
            >
              {error}
            </div>

          )}

        </div>


        {/* ===================================================
            PDF LIST
        =================================================== */}

        <div className="bg-white rounded-2xl shadow p-6">


          {/* -------------------------------------------------
              HEADER
          ------------------------------------------------- */}

          <div className="flex items-center justify-between mb-6">


            <h3 className="text-xl font-bold text-gray-800">
              📚 Uploaded PDFs
            </h3>


            <button
              onClick={loadPDFs}
              disabled={loading}
              className="
                px-4
                py-2
                bg-gray-100
                hover:bg-gray-200
                rounded-lg
                text-gray-700
                font-semibold

                disabled:opacity-60
                disabled:cursor-not-allowed
              "
            >
              🔄 Refresh
            </button>


          </div>


          {/* =================================================
              LOADING
          ================================================= */}

          {loading ? (

            <div className="text-center py-10 text-gray-500">

              Loading PDFs...

            </div>


          ) : pdfs.length === 0 ? (

            /* =================================================
               EMPTY LIBRARY
            ================================================= */

            <div className="text-center py-12">


              <div className="text-6xl mb-4">
                📂
              </div>


              <h4 className="text-xl font-semibold text-gray-700">

                No PDFs uploaded yet

              </h4>


              <p className="text-gray-500 mt-2">

                Upload your first study PDF above.

              </p>


            </div>


          ) : (

            /* =================================================
               PDF CARDS
            ================================================= */

            <div
              className="
                grid
                grid-cols-1
                md:grid-cols-2
                lg:grid-cols-3
                gap-5
              "
            >


              {pdfs.map((pdf) => (

                <div
                  key={pdf.document_id}
                  className="
                    border
                    border-gray-200
                    rounded-xl
                    p-5
                    hover:shadow-md
                    transition
                  "
                >


                  {/* -----------------------------------------
                      PDF INFORMATION
                  ----------------------------------------- */}

                  <div className="flex items-start gap-4">


                    <div className="text-4xl">
                      📄
                    </div>


                    <div className="min-w-0">


                      {/* FILE NAME */}

                      <h4
                        className="
                          font-bold
                          text-gray-800
                          truncate
                        "
                        title={pdf.filename}
                      >
                        {pdf.filename}
                      </h4>


                      {/* PAGE COUNT */}

                      <p className="text-sm text-gray-500 mt-2">

                        📑 {pdf.page_count} pages

                      </p>


                      {/* UPLOAD DATE */}

                      {pdf.uploaded_at && (

                        <p className="text-xs text-gray-400 mt-1">

                          Uploaded:{" "}

                          {new Date(
                            pdf.uploaded_at
                          ).toLocaleDateString()}

                        </p>

                      )}

                    </div>

                  </div>


                  {/* -----------------------------------------
                      DELETE BUTTON
                  ----------------------------------------- */}

                  <div className="mt-4">


                    <button
                      onClick={() =>
                        handleDelete(
                          pdf.document_id,
                          pdf.filename
                        )
                      }
                      disabled={
                        deleting === pdf.document_id
                      }
                      className="
                        w-full
                        bg-red-50
                        hover:bg-red-100
                        text-red-600
                        font-semibold
                        py-2
                        rounded-lg
                        transition

                        disabled:opacity-60
                        disabled:cursor-not-allowed
                      "
                    >

                      {deleting === pdf.document_id
                        ? "Deleting..."
                        : "🗑️ Delete PDF"
                      }

                    </button>


                  </div>


                </div>

              ))}


            </div>

          )}


        </div>


      </main>


    </div>

  );

}


export default Library;
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const getToken = () => {
  return localStorage.getItem("token");
};

export const setToken = (token) => {
  localStorage.setItem("token", token);
};

export const clearToken = () => {
  localStorage.removeItem("token");
};

export const apiFetch = async (endpoint, options = {}) => {
  const token = getToken();

  const headers = {
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }

  return data;
};


// ==================== AUTH ====================

export const registerUser = async (userData) => {
  return apiFetch("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });
};

export const loginUser = async (userData) => {
  return apiFetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });
};

export const logoutUser = async () => {
  return apiFetch("/auth/logout", {
    method: "POST",
  });
};


// ==================== STUDENTS ====================

export const getStudents = async (params = "") => {
  return apiFetch(`/students/${params}`);
};

export const getStudent = async (studentId) => {
  return apiFetch(`/students/${studentId}`);
};

export const createStudent = async (studentData) => {
  return apiFetch("/students/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(studentData),
  });
};

export const updateStudent = async (studentId, studentData) => {
  return apiFetch(`/students/${studentId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(studentData),
  });
};

export const deleteStudent = async (studentId) => {
  return apiFetch(`/students/${studentId}`, {
    method: "DELETE",
  });
};

export const getBranches = async () => {
  return apiFetch("/students/branches");
};

export const getStatistics = async () => {
  return apiFetch("/students/statistics");
};


// ==================== PDF ====================

export const uploadPDF = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/pdf/upload", {
    method: "POST",
    body: formData,
  });
};

export const getPDFLibrary = async () => {
  return apiFetch("/pdf/library");
};

export const askPDFQuestion = async (questionData) => {
  return apiFetch("/pdf/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(questionData),
  });
};

export const reloadPDFs = async () => {
  return apiFetch("/pdf/reload", {
    method: "POST",
  });
};

export const deletePDF = async (documentId) => {
  return apiFetch(`/pdf/library/${documentId}`, {
    method: "DELETE",
  });
};


// ==================== CHAT ====================

export const askChatQuestion = async (question) => {
  return apiFetch("/chat/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: question
    })
  });
};

export const getChatHistory = async () => {
  return apiFetch("/chat/history");
};

export const deleteChatHistory = async (historyId) => {
  return apiFetch(`/chat/history/${historyId}`, {
    method: "DELETE",
  });
};

export const deleteAllChatHistory = async () => {
  return apiFetch("/chat/history", {
    method: "DELETE",
  });
};


// ==================== FLASHCARDS ====================

export const generateFlashcards = async (flashcardData) => {
  return apiFetch("/flashcards/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(flashcardData)
  });
};

export const getFlashcardLibrary = async () => {
  return apiFetch("/flashcards/library");
};

export const deleteFlashcardSet = async (id) => {
  return apiFetch(`/flashcards/library/${id}`, {
    method: "DELETE",
  });
};


// ==================== QUIZ & STUDY GUIDE ====================

export const generateQuiz = async (quizData) => {
  return apiFetch("/quiz/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(quizData),
  });
};

export const getQuizHistory = async () => {
  return apiFetch("/quiz/history");
};

export const deleteQuizHistory = async (historyId) => {
  return apiFetch(`/quiz/history/${historyId}`, {
    method: "DELETE",
  });
};

export const deleteAllQuizHistory = async () => {
  return apiFetch("/quiz/history", {
    method: "DELETE",
  });
};

export const generateStudyGuide = async (studyData) => {
  return apiFetch("/study-guide/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(studyData),
  });
};
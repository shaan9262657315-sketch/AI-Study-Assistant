import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, setToken } from "../services/api";

function Login() {
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // =====================================================
  // HANDLE INPUT CHANGE
  // =====================================================

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });

    setError("");
  };

  // =====================================================
  // LOGIN
  // =====================================================

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");

    if (!formData.email.trim() || !formData.password.trim()) {
      setError("Please enter your email and password.");
      return;
    }

    try {
      setLoading(true);

      const data = await loginUser({
        email: formData.email.trim(),
        password: formData.password,
      });

      // Save JWT token
      setToken(data.access_token);

      // Go to Dashboard
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50 flex items-center justify-center px-4 py-8">

      <div className="w-full max-w-md">

        {/* =================================================
            LOGIN CARD
        ================================================= */}

        <div className="bg-white rounded-3xl shadow-xl border border-gray-100 px-8 py-9">

          {/* =================================================
              LOGO
          ================================================= */}

          <div className="flex justify-center mb-6">

            <div className="w-28 h-28 bg-violet-200 rounded-2xl flex items-center justify-center text-6xl shadow-lg">
              📚
            </div>

          </div>


          {/* =================================================
              HEADING
          ================================================= */}

          <div className="text-center mb-9">

            <h1 className="text-3xl font-bold text-gray-900">
              AI Study Assistant
            </h1>

            <p className="text-sm text-indigo-600 font-semibold mt-2">
              Powered by Shaan AI
            </p>

            <p className="text-gray-500 mt-3">
              Welcome back! Login to continue.
            </p>

          </div>


          {/* =================================================
              LOGIN FORM
          ================================================= */}

          <form
            onSubmit={handleSubmit}
            className="space-y-6"
          >

            {/* =================================================
                EMAIL
            ================================================= */}

            <div>

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Email
              </label>

              <input
                type="email"
                name="email"
                placeholder="Enter your email"
                value={formData.email}
                onChange={handleChange}
                required
                autoComplete="email"
                className="w-full px-4 py-3.5 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
              />

            </div>


            {/* =================================================
                PASSWORD
            ================================================= */}

            <div>

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Password
              </label>

              <div className="relative">

                <input
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  name="password"
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  autoComplete="current-password"
                  className="w-full px-4 py-3.5 pr-12 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
                />

                <button
                  type="button"
                  onClick={() =>
                    setShowPassword(!showPassword)
                  }
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-xl hover:scale-110 transition"
                  title={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  {showPassword ? "👁️" : "👁️‍🗨️"}
                </button>

              </div>

            </div>


            {/* =================================================
                ERROR
            ================================================= */}

            {error && (

              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
                {error}
              </div>

            )}


            {/* =================================================
                LOGIN BUTTON
            ================================================= */}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3.5 rounded-xl transition duration-200 shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
            >

              {loading
                ? "🤖 Logging in..."
                : "Login"}

            </button>

          </form>


          {/* =================================================
              REGISTER
          ================================================= */}

          <div className="text-center mt-8 text-gray-500 text-sm">

            Don't have an account?

            <Link
              to="/register"
              className="ml-1 text-indigo-600 font-semibold hover:text-indigo-700"
            >
              Register
            </Link>

          </div>

        </div>

      </div>

    </div>
  );
}

export default Login;
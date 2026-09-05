import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerUser } from "../services/api";

function Register() {
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    branch: "",
    year: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // =====================================================
  // HANDLE INPUT CHANGE
  // =====================================================

  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // =====================================================
  // SUBMIT
  // =====================================================

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");

    // Basic validation
    if (!formData.name.trim()) {
      setError("Please enter your name.");
      return;
    }

    if (!formData.email.trim()) {
      setError("Please enter your email.");
      return;
    }

    if (!formData.password) {
      setError("Please enter a password.");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (!formData.branch.trim()) {
      setError("Please enter your branch.");
      return;
    }

    if (!formData.year) {
      setError("Please select your year.");
      return;
    }

    try {
      setLoading(true);

      await registerUser({
        ...formData,
        name: formData.name.trim(),
        email: formData.email.trim(),
        branch: formData.branch.trim(),
        year: Number(formData.year),
      });

      // Registration successful
      navigate("/login");

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50 flex items-center justify-center px-4 py-8">

      <div className="w-full max-w-md">

        <div className="bg-white rounded-3xl shadow-xl border border-gray-100 p-8">

          {/* =================================================
              LOGO
          ================================================= */}

          <div className="flex justify-center mb-5">

            <div className="w-20 h-20 bg-indigo-600 rounded-2xl flex items-center justify-center text-4xl shadow-lg">
              📚
            </div>

          </div>


          {/* =================================================
              HEADING
          ================================================= */}

          <div className="text-center mb-8">

            <h1 className="text-3xl font-bold text-gray-900">
              Create Account
            </h1>

            <p className="text-gray-500 mt-2">
              Join AI Study Assistant today.
            </p>

          </div>


          {/* =================================================
              FORM
          ================================================= */}

          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >

            {/* NAME */}

            <div>

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Name
              </label>

              <input
                type="text"
                name="name"
                placeholder="Enter your name"
                value={formData.name}
                onChange={handleChange}
                disabled={loading}
                autoComplete="name"
                required
                className="w-full px-4 py-3.5 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition disabled:bg-gray-100"
              />

            </div>


            {/* EMAIL */}

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
                disabled={loading}
                autoComplete="email"
                required
                className="w-full px-4 py-3.5 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition disabled:bg-gray-100"
              />

            </div>


            {/* PASSWORD */}

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
                  placeholder="Create a password"
                  value={formData.password}
                  onChange={handleChange}
                  disabled={loading}
                  autoComplete="new-password"
                  required
                  minLength={6}
                  className="w-full px-4 py-3.5 pr-12 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition disabled:bg-gray-100"
                />

                <button
                  type="button"
                  onClick={() =>
                    setShowPassword((prev) => !prev)
                  }
                  disabled={loading}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-xl hover:scale-110 transition disabled:opacity-50"
                  title={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  {showPassword ? "🔓" : "🔒"}
                </button>

              </div>

              <p className="text-xs text-gray-400 mt-2">
                Password must be at least 6 characters.
              </p>

            </div>


            {/* BRANCH */}

            <div>

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Branch
              </label>

              <input
                type="text"
                name="branch"
                placeholder="e.g. CSE"
                value={formData.branch}
                onChange={handleChange}
                disabled={loading}
                required
                className="w-full px-4 py-3.5 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition disabled:bg-gray-100"
              />

            </div>


            {/* YEAR */}

            <div>

              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Year
              </label>

              <select
                name="year"
                value={formData.year}
                onChange={handleChange}
                disabled={loading}
                required
                className="w-full px-4 py-3.5 border border-gray-300 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition disabled:bg-gray-100"
              >

                <option value="">
                  Select Year
                </option>

                <option value="1">
                  1st Year
                </option>

                <option value="2">
                  2nd Year
                </option>

                <option value="3">
                  3rd Year
                </option>

                <option value="4">
                  4th Year
                </option>

              </select>

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
                REGISTER BUTTON
            ================================================= */}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3.5 rounded-xl transition duration-200 shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
            >

              {loading
                ? "Creating Account..."
                : "Create Account"
              }

            </button>

          </form>


          {/* =================================================
              LOGIN
          ================================================= */}

          <div className="text-center mt-7 text-gray-500 text-sm">

            Already have an account?

            <Link
              to="/login"
              className="ml-1 text-indigo-600 font-semibold hover:text-indigo-700 transition"
            >
              Login
            </Link>

          </div>

        </div>

      </div>

    </div>
  );
}

export default Register;
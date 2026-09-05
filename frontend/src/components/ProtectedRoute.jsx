import { Navigate, useLocation } from "react-router-dom";
import { getToken } from "../services/api";

function ProtectedRoute({ children }) {
  const location = useLocation();

  const token = getToken();

  // User logged in nahi hai
  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  // User logged in hai
  return children;
}

export default ProtectedRoute;
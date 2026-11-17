import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import "./index.css";
import { ForgotPasswordPage, LoginPage, RegisterPage, ResetPasswordPage } from "./pages/AuthPages";
import CoursePage from "./pages/course/CoursePage";
import CreditsPage from "./pages/CreditsPage";
import DashboardPage from "./pages/DashboardPage";
import GradeHistoryPage from "./pages/GradeHistoryPage";
import ImportExportPage from "./pages/ImportExportPage";
import SemesterPage from "./pages/SemesterPage";
import SemestersPage from "./pages/SemestersPage";
import SettingsPage from "./pages/SettingsPage";

function App() {
  const { account } = useAuth();
  if (account === undefined) return null; // still checking whether a session exists

  if (account === null) {
    return (
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="semesters" element={<SemestersPage />} />
        <Route path="semesters/:semesterId" element={<SemesterPage />} />
        <Route path="courses/:courseId" element={<CoursePage />} />
        <Route path="history" element={<GradeHistoryPage />} />
        <Route path="credits" element={<CreditsPage />} />
        <Route path="import-export" element={<ImportExportPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="reset-password" element={<ResetPasswordPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);

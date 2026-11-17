// The screens shown before logging in: log in, register, forgot password, reset password.
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { Button, ErrorMessage, Field } from "../components/ui";
import type { Account } from "../types";

function AuthFrame({ title, onSubmit, error, children, footer }: {
  title: string;
  onSubmit: () => void;
  error?: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 text-slate-800">
      <form onSubmit={submit} className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-1 text-lg font-bold text-indigo-700">CGPA Tracker</div>
        <h1 className="mb-4 text-xl font-semibold text-slate-900">{title}</h1>
        <ErrorMessage message={error} />
        <div className="flex flex-col gap-3">{children}</div>
        <div className="mt-4 flex flex-col gap-1 text-sm text-slate-500">{footer}</div>
      </form>
    </div>
  );
}

const linkClass = "text-indigo-700 hover:underline";

export function LoginPage() {
  const { setAccount } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const { run, error, busy } = useAction();
  const login = () => run(async () => setAccount(await api.post<Account>("/api/auth/login", form)));

  return (
    <AuthFrame title="Log in" onSubmit={login} error={error} footer={<>
      <Link className={linkClass} to="/forgot-password">Forgot your password?</Link>
      <span>No account yet? <Link className={linkClass} to="/register">Register</Link></span>
    </>}>
      <Field label="Email"><input type="email" required autoComplete="email" value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Password"><input type="password" required autoComplete="current-password" value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
      <Button type="submit" disabled={busy}>Log in</Button>
    </AuthFrame>
  );
}

export function RegisterPage() {
  const { setAccount } = useAuth();
  const status = useApi<{ local_data_available: boolean }>("/api/auth/status");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", claim_local_data: true });
  const { run, error, busy } = useAction();
  const canClaim = status.data?.local_data_available ?? false;
  const register = () => run(async () =>
    setAccount(await api.post<Account>("/api/auth/register", { ...form, claim_local_data: canClaim && form.claim_local_data })));

  return (
    <AuthFrame title="Create an account" onSubmit={register} error={error}
      footer={<span>Already registered? <Link className={linkClass} to="/login">Log in</Link></span>}>
      <Field label="Name"><input required autoComplete="name" value={form.full_name}
        onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
      <Field label="Email"><input type="email" required autoComplete="email" value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Password (at least 8 characters)"><input type="password" required minLength={8} autoComplete="new-password"
        value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
      {canClaim && (
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input type="checkbox" className="mt-0.5" checked={form.claim_local_data}
            onChange={(e) => setForm({ ...form, claim_local_data: e.target.checked })} />
          Keep the semesters, courses and grades already entered in this app (from before accounts existed)
        </label>
      )}
      <Button type="submit" disabled={busy}>Create account</Button>
    </AuthFrame>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { run, error, busy } = useAction();
  const send = () => run(() => api.post("/api/auth/forgot-password", { email })).then((ok) => ok && setSent(true));

  return (
    <AuthFrame title="Reset your password" onSubmit={send} error={error}
      footer={<Link className={linkClass} to="/login">Back to log in</Link>}>
      {sent ? (
        <p className="text-sm text-slate-600">If an account uses {email}, a reset link is on its way. It works for one hour.</p>
      ) : (
        <>
          <Field label="Email"><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Button type="submit" disabled={busy}>Send reset link</Button>
        </>
      )}
    </AuthFrame>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const { run, error, busy } = useAction();
  const reset = () =>
    run(() => api.post("/api/auth/reset-password", { token: params.get("token"), password }))
      .then((ok) => ok && navigate("/login"));

  return (
    <AuthFrame title="Choose a new password" onSubmit={reset} error={error}
      footer={<Link className={linkClass} to="/login">Back to log in</Link>}>
      <Field label="New password (at least 8 characters)"><input type="password" required minLength={8}
        autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      <Button type="submit" disabled={busy}>Save password</Button>
    </AuthFrame>
  );
}

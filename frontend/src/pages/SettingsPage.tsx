import { useState } from "react";
import { api, useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { Button, Card, ErrorMessage, Field, Loading, PageHeader, RemoveButton, UnsavedNote, tableClass } from "../components/ui";
import type { Account, CourseType, CreditCategory, Curriculum, GradeEntry, GradingScheme, ProfileData } from "../types";

export default function SettingsPage() {
  const { setAccount } = useAuth();
  const profile = useApi<ProfileData>("/api/profile");
  const schemes = useApi<GradingScheme[]>("/api/grading-schemes");
  const curricula = useApi<Curriculum[]>("/api/curricula");

  if (!profile.data || !schemes.data || !curricula.data) return <Loading error={profile.error ?? schemes.error ?? curricula.error} />;
  const scheme = schemes.data.find((s) => s.id === profile.data!.settings.default_grading_scheme_id);
  const curriculum = curricula.data.find((c) => c.id === profile.data!.profile.curriculum_version_id);
  const reloadAll = () => {
    profile.reload();
    schemes.reload();
    curricula.reload();
    api.get<Account>("/api/auth/me").then(setAccount); // the name shown in the menu
  };

  return (
    <>
      <PageHeader title="Settings" />
      <ProfileCard key={JSON.stringify(profile.data)} data={profile.data} schemes={schemes.data} curricula={curricula.data} onSaved={reloadAll} />
      {scheme && <GradingSchemeCard key={scheme.id} scheme={scheme} onSaved={reloadAll} />}
      {curriculum && <CurriculumCard key={curriculum.id} curriculum={curriculum} profile={profile.data} onSaved={reloadAll} />}
      <CourseTypesCard />
      <AccountCard />
    </>
  );
}

function ProfileCard({ data, schemes, curricula, onSaved }: {
  data: ProfileData;
  schemes: GradingScheme[];
  curricula: Curriculum[];
  onSaved: () => void;
}) {
  const [profile, setProfile] = useState(data.profile);
  const [settings, setSettings] = useState(data.settings);
  const { run, error, busy } = useAction();
  const number = (value: string) => (value === "" ? null : Number(value));
  const save = () => run(() => api.put("/api/profile", { profile, settings })).then((ok) => ok && onSaved());
  const dirty = JSON.stringify({ profile, settings }) !== JSON.stringify(data);

  return (
    <Card title="Profile" actions={<>{dirty && <UnsavedNote />}<Button onClick={save} disabled={busy || !dirty}>{busy ? "Saving…" : "Save profile"}</Button></>}>
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <Field label="Name"><input value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} /></Field>
        <Field label="Specialisation">
          <input value={profile.specialisation ?? ""} onChange={(e) => setProfile({ ...profile, specialisation: e.target.value || null })} />
        </Field>
        <Field label="Curriculum">
          <select value={profile.curriculum_version_id ?? ""} onChange={(e) => setProfile({ ...profile, curriculum_version_id: e.target.value || null })}>
            <option value="">— none —</option>
            {curricula.map((c) => <option key={c.id} value={c.id}>{c.version_name}{c.user_id ? "" : " (shared)"}</option>)}
          </select>
        </Field>
        <Field label="Admission year">
          <input type="number" value={profile.admission_year ?? ""} onChange={(e) => setProfile({ ...profile, admission_year: number(e.target.value) })} />
        </Field>
        <Field label="Expected graduation year">
          <input type="number" value={profile.graduation_year ?? ""} onChange={(e) => setProfile({ ...profile, graduation_year: number(e.target.value) })} />
        </Field>
        <Field label="Target CGPA">
          <input type="number" step={0.01} min={0} max={10} value={settings.target_cgpa ?? ""}
            onChange={(e) => setSettings({ ...settings, target_cgpa: number(e.target.value) })} />
        </Field>
        <Field label="Grading scheme for new courses">
          <select value={settings.default_grading_scheme_id ?? ""} onChange={(e) => setSettings({ ...settings, default_grading_scheme_id: e.target.value || null })}>
            {schemes.map((s) => <option key={s.id} value={s.id}>{s.name} (v{s.version})</option>)}
          </select>
        </Field>
        <label className="col-span-2 flex items-center gap-2 self-end text-sm text-slate-600">
          <input type="checkbox" checked={settings.round_marks_before_grading}
            onChange={(e) => setSettings({ ...settings, round_marks_before_grading: e.target.checked })} />
          Round total marks to the nearest whole number before predicting a grade
        </label>
      </div>
    </Card>
  );
}

const NEW_GRADE: GradeEntry = { grade: "", grade_point: 0, minimum_marks: null, maximum_marks: null, is_passing: true };

function GradingSchemeCard({ scheme, onSaved }: { scheme: GradingScheme; onSaved: () => void }) {
  const [name, setName] = useState(scheme.name);
  const [entries, setEntries] = useState(scheme.entries);
  const { run, error, busy } = useAction();
  const update = (index: number, changes: Partial<GradeEntry>) => setEntries(entries.map((e, i) => (i === index ? { ...e, ...changes } : e)));
  const optionalNumber = (value: string) => (value === "" ? null : Number(value));
  const save = () => run(() => api.put(`/api/grading-schemes/${scheme.id}`, { name, entries })).then((ok) => ok && onSaved());
  const dirty = name !== scheme.name || JSON.stringify(entries) !== JSON.stringify(scheme.entries);

  return (
    <Card title={`Grading scheme · version ${scheme.version}`}
      actions={<>{dirty && <UnsavedNote />}<Button onClick={save} disabled={busy || !dirty}>Save as new version</Button></>}>
      <ErrorMessage message={error} />
      <p className="mb-3 text-sm text-slate-500">
        Saving creates a new version. Courses in progress switch to it; results already recorded keep the version they were graded with.
        Leave the minimum empty for grades that are only awarded, never predicted (e.g. P, N).
      </p>
      <Field label="Name" className="mb-3 w-72"><input value={name} onChange={(e) => setName(e.target.value)} /></Field>
      <table className={tableClass}>
        <thead><tr><th>Grade</th><th>Grade point</th><th>Minimum marks</th><th>Maximum marks</th><th>Passing</th><th></th></tr></thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr key={i}>
              <td><input className="w-16" value={entry.grade} onChange={(e) => update(i, { grade: e.target.value })} /></td>
              <td><input type="number" step="any" className="w-20" value={entry.grade_point} onChange={(e) => update(i, { grade_point: Number(e.target.value) })} /></td>
              <td><input type="number" step="any" className="w-24" value={entry.minimum_marks ?? ""} onChange={(e) => update(i, { minimum_marks: optionalNumber(e.target.value) })} /></td>
              <td><input type="number" step="any" className="w-24" value={entry.maximum_marks ?? ""} onChange={(e) => update(i, { maximum_marks: optionalNumber(e.target.value) })} /></td>
              <td><input type="checkbox" checked={entry.is_passing} onChange={(e) => update(i, { is_passing: e.target.checked })} /></td>
              <td><RemoveButton label={`Remove grade ${entry.grade || "row"}`} onClick={() => setEntries(entries.filter((_, j) => j !== i))} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button className="mt-3" variant="secondary" onClick={() => setEntries([...entries, NEW_GRADE])}>Add grade</Button>
    </Card>
  );
}

const NEW_CATEGORY: CreditCategory = { code: "", name: "", required_credits: 0 };

function CurriculumCard({ curriculum, profile, onSaved }: { curriculum: Curriculum; profile: ProfileData; onSaved: () => void }) {
  const [categories, setCategories] = useState(curriculum.categories);
  const { run, error, busy } = useAction();
  const isShared = curriculum.user_id === null;
  const total = categories.reduce((sum, c) => sum + c.required_credits, 0);
  const update = (index: number, changes: Partial<CreditCategory>) =>
    setCategories(categories.map((c, i) => (i === index ? { ...c, ...changes } : c)));

  const makeCopy = () =>
    run(async () => {
      const copy = await api.post<Curriculum>(`/api/curricula/${curriculum.id}/copy`);
      await api.put("/api/profile", { ...profile, profile: { ...profile.profile, curriculum_version_id: copy.id } });
    }).then((ok) => ok && onSaved());
  const save = () => run(() => api.put(`/api/curricula/${curriculum.id}`, { ...curriculum, categories })).then((ok) => ok && onSaved());
  const dirty = JSON.stringify(categories) !== JSON.stringify(curriculum.categories);

  return (
    <Card title={`Credit requirements · ${curriculum.version_name}`}
      actions={isShared
        ? <Button variant="secondary" onClick={makeCopy} disabled={busy}>Make an editable copy</Button>
        : <>{dirty && <UnsavedNote />}<Button onClick={save} disabled={busy || !dirty}>Save requirements</Button></>}>
      <ErrorMessage message={error} />
      {isShared && <p className="mb-3 text-sm text-slate-600">This is the shared VIT curriculum, which you can't edit. Make an editable copy to change its requirements; your record switches to the copy.</p>}
      <table className={tableClass}>
        <thead><tr><th>Code</th><th>Category</th><th>Required credits</th><th></th></tr></thead>
        <tbody>
          {categories.map((c, i) => (
            <tr key={i}>
              <td><input disabled={isShared} className="w-24" value={c.code} onChange={(e) => update(i, { code: e.target.value.toUpperCase() })} /></td>
              <td><input disabled={isShared} className="w-96" value={c.name} onChange={(e) => update(i, { name: e.target.value })} /></td>
              <td><input disabled={isShared} type="number" min={0} step={0.5} className="w-24" value={c.required_credits}
                onChange={(e) => update(i, { required_credits: Number(e.target.value) })} /></td>
              <td>{!isShared && <RemoveButton label={`Remove category ${c.code || "row"}`} onClick={() => setCategories(categories.filter((_, j) => j !== i))} />}</td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr><td className="px-2 py-2 font-medium" colSpan={2}>Total</td><td className="px-2 font-medium">{total}</td><td></td></tr></tfoot>
      </table>
      {!isShared && <Button className="mt-3" variant="secondary" onClick={() => setCategories([...categories, NEW_CATEGORY])}>Add category</Button>}
    </Card>
  );
}

function CourseTypesCard() {
  const types = useApi<CourseType[]>("/api/course-types");
  const [draft, setDraft] = useState({ code: "", name: "" });
  const { run, error, busy } = useAction();
  const add = () =>
    run(() => api.post("/api/course-types", draft)).then((ok) => {
      if (ok) {
        setDraft({ code: "", name: "" });
        types.reload();
      }
    });

  return (
    <Card title="Course types">
      <ErrorMessage message={error} />
      <div className="mb-4 flex flex-wrap gap-2">
        {types.data?.map((t) => (
          <span key={t.id} className="rounded-md bg-slate-100 px-2 py-1 text-sm"><strong>{t.code}</strong> {t.name}</span>
        ))}
      </div>
      <div className="flex items-end gap-3">
        <Field label="Code"><input className="w-24" value={draft.code} onChange={(e) => setDraft({ ...draft, code: e.target.value.toUpperCase() })} /></Field>
        <Field label="Name"><input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field>
        <Button variant="secondary" onClick={add} disabled={busy || !draft.code || !draft.name}>Add type</Button>
      </div>
    </Card>
  );
}

function AccountCard() {
  const { account, setAccount } = useAuth();
  const [email, setEmail] = useState({ email: account!.email, password: "" });
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [deletion, setDeletion] = useState({ password: "" });
  const [message, setMessage] = useState<string>();
  const { run, error, busy } = useAction();

  const done = (text: string) => (ok: boolean) => ok && setMessage(text);
  const changeEmail = () =>
    run(async () => setAccount(await api.put<Account>("/api/auth/email", email))).then(done("Email changed."));
  const changePassword = () =>
    run(() => api.put("/api/auth/password", password)).then(done("Password changed. Other devices have been logged out."));
  const deleteAccount = () => {
    if (!confirm("Delete your account and every semester, course and grade in it? This cannot be undone.")) return;
    run(() => api.post("/api/auth/delete-account", deletion)).then((ok) => ok && setAccount(null));
  };

  return (
    <Card title="Account">
      <ErrorMessage message={error} />
      {message && <p className="mb-4 text-sm text-emerald-700">{message}</p>}
      <div className="grid gap-6 md:grid-cols-3">
        <div className="flex flex-col gap-2">
          <Field label="Email"><input type="email" value={email.email} onChange={(e) => setEmail({ ...email, email: e.target.value })} /></Field>
          <Field label="Current password"><input type="password" value={email.password}
            onChange={(e) => setEmail({ ...email, password: e.target.value })} /></Field>
          <Button variant="secondary" onClick={changeEmail} disabled={busy}>Change email</Button>
        </div>
        <div className="flex flex-col gap-2">
          <Field label="Current password"><input type="password" value={password.current_password}
            onChange={(e) => setPassword({ ...password, current_password: e.target.value })} /></Field>
          <Field label="New password (at least 8 characters)"><input type="password" value={password.new_password}
            onChange={(e) => setPassword({ ...password, new_password: e.target.value })} /></Field>
          <Button variant="secondary" onClick={changePassword} disabled={busy}>Change password</Button>
        </div>
        <div className="flex flex-col gap-2">
          <Field label="Current password"><input type="password" value={deletion.password}
            onChange={(e) => setDeletion({ password: e.target.value })} /></Field>
          <Button variant="danger" onClick={deleteAccount} disabled={busy}>Delete account and all data</Button>
        </div>
      </div>
    </Card>
  );
}

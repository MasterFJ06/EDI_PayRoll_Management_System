import { useState, type FormEvent } from "react";
import { ArrowLeft, ClipboardPlus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, apiClient, type AttendanceCreateRequest, type AttendanceCreateResponse, type AttendanceStatus } from "../api/client";

export function CreateAttendancePage() {
  const navigate = useNavigate();
  const [employeeId, setEmployeeId] = useState("");
  const [date, setDate] = useState("");
  const [status, setStatus] = useState<AttendanceStatus>("PRESENT");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage(null);
    if (checkIn && checkOut && checkOut < checkIn) { setMessage({ kind: "error", text: "Check-out cannot be earlier than check-in." }); return; }
    const request: AttendanceCreateRequest = { employee_id: Number(employeeId), attendance_date: date, attendance_status: status, check_in_time: checkIn ? `${checkIn}:00` : null, check_out_time: checkOut ? `${checkOut}:00` : null };
    setBusy(true);
    try {
      const created = await apiClient.post<AttendanceCreateResponse>("/attendance", request);
      setMessage({ kind: "success", text: `Attendance record ${created.attendance_id} was created.` });
      window.setTimeout(() => navigate("/attendance"), 700);
    } catch (error) {
      setMessage({ kind: "error", text: error instanceof ApiError ? error.message : "Attendance could not be recorded. Check the API connection and try again." });
    } finally { setBusy(false); }
  }
  const input = "mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10";
  return <div className="mx-auto max-w-2xl space-y-5"><Link to="/attendance" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700"><ArrowLeft size={16} />Attendance</Link><section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"><div className="mb-6 flex items-start gap-3"><div className="grid size-10 place-items-center rounded-lg bg-blue-50 text-blue-700"><ClipboardPlus size={18} /></div><div><p className="text-xs text-slate-400">Workforce</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Record attendance</h2><p className="mt-1 text-sm text-slate-500">Attendance status and timestamps are stored as entered.</p></div></div><form className="space-y-4" onSubmit={submit}><label className="block text-xs font-semibold text-slate-600">Employee ID<input required min="1" step="1" type="number" className={input} value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} /></label><label className="block text-xs font-semibold text-slate-600">Attendance date<input required type="date" className={input} value={date} onChange={(e) => setDate(e.target.value)} /></label><label className="block text-xs font-semibold text-slate-600">Status<select className={input} value={status} onChange={(e) => setStatus(e.target.value as AttendanceStatus)}>{(["PRESENT", "ABSENT", "HALF_DAY", "ON_LEAVE", "HOLIDAY"] as const).map((item) => <option key={item}>{item}</option>)}</select></label><div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold text-slate-600">Check-in (optional)<input type="datetime-local" className={input} value={checkIn} onChange={(e) => setCheckIn(e.target.value)} /></label><label className="text-xs font-semibold text-slate-600">Check-out (optional)<input type="datetime-local" className={input} value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></label></div><p className="text-xs leading-5 text-slate-400">The API requires an existing employee and permits one attendance record per employee per date. It does not expose an employee lookup here; enter the persisted employee ID.</p>{message && <div role={message.kind === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm ${message.kind === "error" ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{message.text}</div>}<button disabled={busy} className="inline-flex h-10 w-full items-center justify-center rounded-lg bg-blue-700 px-5 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-wait disabled:opacity-60">{busy ? "Saving…" : "Save attendance"}</button></form></section></div>;
}

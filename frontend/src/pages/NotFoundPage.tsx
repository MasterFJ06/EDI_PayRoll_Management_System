import { Link } from "react-router-dom";

export function NotFoundPage() {
  return <main className="grid min-h-screen place-items-center bg-slate-50 px-6 text-center"><div><p className="text-sm font-semibold text-blue-700">404 · Page not found</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">This page is not available</h1><p className="mt-2 text-sm text-slate-500">The address may be incorrect or the page may not be part of this frontend.</p><Link to="/" className="mt-5 inline-flex h-10 items-center rounded-lg bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-600/20">Return to workspace</Link></div></main>;
}

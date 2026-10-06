import Link from "next/link";

export default function NotFound() {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-10 text-center">
      <p className="text-sm font-medium text-slate-300">404 — page not found</p>
      <p className="mt-2 text-sm text-slate-500">
        This route does not exist in the navigation configuration.
      </p>
      <Link
        href="/"
        className="mt-6 inline-block rounded-md bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700"
      >
        Back to dashboard
      </Link>
    </div>
  );
}

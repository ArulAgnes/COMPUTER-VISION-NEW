"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, NAV_ITEMS } from "@/lib/navigation";

function navClass(active: boolean): string {
  return [
    "block rounded-md px-3 py-2 text-sm transition-colors",
    active
      ? "bg-slate-800 text-white font-medium"
      : "text-slate-400 hover:text-white hover:bg-slate-800/60",
  ].join(" ");
}

/** Sidebar navigation shared by every route. */
export default function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 flex-col border-r border-slate-800 bg-slate-950">
        <div className="border-b border-slate-800 px-5 py-5">
          <p className="text-sm font-semibold tracking-wide text-white">
            Computer Vision New
          </p>
          <p className="mt-1 text-xs text-slate-500">Data-centric CV platform</p>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {NAV_GROUPS.map((group) => (
            <div key={group}>
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {group}
              </p>
              <div className="space-y-1">
                {NAV_ITEMS.filter((item) => item.group === group).map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={navClass(pathname === item.href)}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-5 py-4 text-xs text-slate-500">
          Stage 1 skeleton
        </div>
      </aside>

      {/* Mobile navigation */}
      <div className="lg:hidden sticky top-0 z-20 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
        <div className="px-4 py-3">
          <p className="text-sm font-semibold text-white">Computer Vision New</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "whitespace-nowrap rounded-md px-3 py-1.5 text-xs",
                pathname === item.href
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:text-white",
              ].join(" ")}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </>
  );
}

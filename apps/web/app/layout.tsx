import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Computer Vision New",
  description:
    "Data-centric closed-loop computer vision platform: data, annotation, training, evaluation, error analysis, diagnosis and recommendations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-950 text-slate-200">
        <Sidebar />
        <div className="lg:pl-64">
          <main className="mx-auto w-full max-w-6xl px-4 py-6 lg:px-8 lg:py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

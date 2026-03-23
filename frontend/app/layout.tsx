import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Swiss Municipality Analytics",
  description: "Multi-dimensional analytics platform for Swiss municipalities",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <nav className="bg-swiss-dark text-white px-6 py-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <a href="/" className="text-xl font-bold">
                Swiss Municipality Analytics
              </a>
              <div className="flex gap-6 text-sm">
                <a href="/rankings" className="hover:text-swiss-light transition">
                  Rankings
                </a>
                <a href="/compare" className="hover:text-swiss-light transition">
                  Compare
                </a>
                <a href="/map" className="hover:text-swiss-light transition">
                  Map
                </a>
              </div>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

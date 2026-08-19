import type { Metadata } from "next";
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Providers } from "@/components/providers";
import "./globals.css";

// Geist fonts are pre-configured via the imported modules
// We use their built-in variable properties directly

export const metadata: Metadata = {
  title: "DataSentinel | Operations Center",
  description: "Enterprise healthcare data pipeline monitoring, data-quality, anomaly detection, and incident response platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
      <html
        lang="en"
        className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
      >
      <body className="min-h-full flex h-full bg-canvas text-primary overflow-hidden">
        <Providers>
          <Sidebar />
          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto bg-canvas p-6 outline-none" tabIndex={-1}>
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

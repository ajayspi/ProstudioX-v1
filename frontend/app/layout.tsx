import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prostudio v1",
  description:
    "Faceless finance Shorts studio — turn a topic into a finished 9:16 video.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}

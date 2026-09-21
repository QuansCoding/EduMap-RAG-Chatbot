import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EduMap Study Assistant",
  description: "Collaborative, AI-powered study workspaces grounded in your course materials.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

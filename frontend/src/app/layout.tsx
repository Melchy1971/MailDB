import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MailKnowledge",
  description: "Intelligent email management and knowledge extraction",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

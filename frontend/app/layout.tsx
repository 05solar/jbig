import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JB Bridge AI",
  description: "낯선 전북 생활을 하나로 잇다",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}


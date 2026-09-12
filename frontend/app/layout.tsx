// 전역 레이아웃과 사이트 메타데이터를 정의하는 파일
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JBIG — Jeonbuk International Gateway",
  description: "전북 거주 외국인을 위한 AI 정착지원 플랫폼",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}


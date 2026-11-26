import type { Metadata } from "next";
import { CartProvider } from "@/context/CartContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "Shopping Agent — AI Pantry Assistant",
  description: "Conversational shopping assistant with FastAPI, PostgreSQL, and LangChain.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased text-slate-900 bg-slate-50">
        <CartProvider>{children}</CartProvider>
      </body>
    </html>
  );
}

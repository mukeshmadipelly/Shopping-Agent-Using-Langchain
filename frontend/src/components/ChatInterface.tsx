"use client";

import React, { useEffect, useRef, useState } from "react";
import { ImagePlus, Loader2, Send, ShoppingBag, Sparkles, X } from "lucide-react";
import { CartDrawer } from "@/components/CartDrawer";
import { ProductCard } from "@/components/ProductCard";
import { useCart } from "@/context/CartContext";
import type { ChatMessage, Product } from "@/types/shop";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const STARTER_PROMPTS = [
  "Show me organic snacks under $15",
  "Find organic honey with 4.5+ rating",
  "What coffee or tea do you recommend?",
  "Show my order history",
];

function renderFormattedText(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={idx} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={idx} className="italic">
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={idx} className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono text-slate-800">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

export function ChatInterface() {
  const { sessionId, cart, syncCartFromAgent, refreshOrders } = useCart();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<{
    base64: string;
    mime: string;
    preview: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const scrollEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (!sessionId) return;
    fetch(`${API_BASE}/api/chat/history`, {
      headers: { "X-Session-Id": sessionId },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.messages?.length) {
          setMessages(
            data.messages.map((m: { role: "user" | "assistant"; content: string }, i: number) => ({
              id: `hist-${i}`,
              role: m.role,
              content: m.content,
            }))
          );
        }
      })
      .catch(() => {});
  }, [sessionId]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const [header, base64] = dataUrl.split(",");
      const mimeMatch = header.match(/data:(.*?);/);
      setSelectedImage({
        base64,
        mime: mimeMatch ? mimeMatch[1] : file.type || "image/jpeg",
        preview: dataUrl,
      });
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const sendMessage = async (textToSend?: string) => {
    const content = (textToSend ?? input).trim();
    if ((!content && !selectedImage) || isStreaming || !sessionId) return;

    setErrorBanner(null);
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content || "Find products similar to this image",
      imagePreview: selectedImage?.preview,
    };

    const assistantId = `assistant-${Date.now()}`;
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
    };

    const imagePayload = selectedImage;
    setSelectedImage(null);
    if (!textToSend) setInput("");
    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setIsStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          message: userMsg.content,
          image_base64: imagePayload?.base64 ?? null,
          image_mime: imagePayload?.mime ?? null,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          let eventType = "message";
          let dataLine = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLine += line.slice(5).trim();
            }
          }
          if (!dataLine) continue;
          const payload = JSON.parse(dataLine);

          if (eventType === "token" && payload.text) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + payload.text } : m
              )
            );
          } else if (eventType === "products" && Array.isArray(payload.products)) {
            const products: Product[] = payload.products;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, products } : m))
            );
          } else if (eventType === "cart" && payload.cart) {
            syncCartFromAgent(payload.cart);
          } else if (eventType === "order" && payload.order) {
            refreshOrders();
          } else if (eventType === "error") {
            setErrorBanner(payload.detail || "Something went wrong.");
          }
        }
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Failed to reach shopping agent.");
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* Top Bar */}
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900">Shopping Agent</h1>
            <p className="text-xs text-slate-500">AI Pantry &amp; Grocery Assistant</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50"
        >
          <ShoppingBag className="h-4 w-4" />
          <span>Cart</span>
          <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white">
            {cart.total_items}
          </span>
        </button>
      </header>

      {/* Error Banner */}
      {errorBanner && (
        <div className="mx-auto mt-3 flex w-full max-w-4xl items-center justify-between rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          <span>{errorBanner}</span>
          <button type="button" onClick={() => setErrorBanner(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {messages.length === 0 ? (
            <div className="mt-12 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">
                What can I help you shop for today?
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Search 85+ organic &amp; pantry items, compare ratings, upload a product photo, or
                manage your cart right in chat.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${
                  msg.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-slate-900 text-white"
                      : "border border-slate-200 bg-white text-slate-800 shadow-sm"
                  }`}
                >
                  {msg.imagePreview && (
                    <img
                      src={msg.imagePreview}
                      alt="Uploaded product"
                      className="mb-2 max-h-44 rounded-lg object-cover"
                    />
                  )}
                  <div className="whitespace-pre-wrap">
                    {msg.content
                      ? renderFormattedText(msg.content)
                      : isStreaming && msg.role === "assistant"
                      ? "Thinking..."
                      : ""}
                  </div>
                </div>

                {msg.products && msg.products.length > 0 && (
                  <div className="mt-3 grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {msg.products.map((product) => (
                      <ProductCard key={product.id} product={product} />
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={scrollEndRef} />
        </div>
      </main>

      {/* Composer */}
      <footer className="border-t border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto max-w-4xl">
          {selectedImage && (
            <div className="mb-2 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-1.5">
              <img
                src={selectedImage.preview}
                alt="Preview"
                className="h-10 w-10 rounded object-cover"
              />
              <span className="text-xs text-slate-600">Image attached</span>
              <button
                type="button"
                onClick={() => setSelectedImage(null)}
                className="rounded p-0.5 text-slate-400 hover:text-slate-700"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isStreaming}
              title="Upload product image for visual search"
              className="rounded-xl border border-slate-200 p-2.5 text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
            >
              <ImagePlus className="h-5 w-5" />
            </button>

            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for products, add to cart, or checkout..."
              disabled={isStreaming}
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:bg-white focus:outline-none"
            />

            <button
              type="submit"
              disabled={isStreaming || (!input.trim() && !selectedImage)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </footer>

      <CartDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}

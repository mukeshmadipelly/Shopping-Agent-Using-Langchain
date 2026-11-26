"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { CartState, Order } from "@/types/shop";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const SESSION_KEY = "shopping_agent_session_id";

interface CartContextValue {
  sessionId: string;
  cart: CartState;
  orders: Order[];
  isLoading: boolean;
  addToCart: (productId: number, qty?: number) => Promise<void>;
  removeFromCart: (productId: number, qty?: number) => Promise<void>;
  clearCart: () => Promise<void>;
  checkout: () => Promise<Order | null>;
  refreshCart: () => Promise<void>;
  refreshOrders: () => Promise<void>;
  syncCartFromAgent: (nextCart: CartState) => void;
}

const emptyCart = (sessionId: string): CartState => ({
  session_id: sessionId,
  items: [],
  total_items: 0,
  total_amount: 0,
});

const CartContext = createContext<CartContextValue | undefined>(undefined);

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "default-session";
  const existing = window.localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().slice(0, 12)
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  const generated = `sess-${randomPart}`;
  window.localStorage.setItem(SESSION_KEY, generated);
  return generated;
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string>("");
  const [cart, setCart] = useState<CartState>(() => emptyCart(""));
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    const sid = getOrCreateSessionId();
    setSessionId(sid);
    setCart(emptyCart(sid));
  }, []);

  const refreshCart = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/api/cart`, {
        headers: { "X-Session-Id": sessionId },
      });
      if (res.ok) {
        const data: CartState = await res.json();
        setCart(data);
      }
    } catch {
      // Backend might still be starting up
    }
  }, [sessionId]);

  const refreshOrders = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/api/orders`, {
        headers: { "X-Session-Id": sessionId },
      });
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders || []);
      }
    } catch {
      // Ignore network errors during initial load
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) {
      refreshCart();
      refreshOrders();
    }
  }, [sessionId, refreshCart, refreshOrders]);

  const addToCart = useCallback(
    async (productId: number, qty = 1) => {
      if (!sessionId) return;
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/cart/items`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-Id": sessionId,
          },
          body: JSON.stringify({ product_id: productId, qty }),
        });
        if (res.ok) {
          setCart(await res.json());
        }
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const removeFromCart = useCallback(
    async (productId: number, qty?: number) => {
      if (!sessionId) return;
      setIsLoading(true);
      try {
        const qs = qty ? `?qty=${qty}` : "";
        const res = await fetch(`${API_BASE}/api/cart/items/${productId}${qs}`, {
          method: "DELETE",
          headers: { "X-Session-Id": sessionId },
        });
        if (res.ok) {
          setCart(await res.json());
        }
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const clearCart = useCallback(async () => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/cart`, {
        method: "DELETE",
        headers: { "X-Session-Id": sessionId },
      });
      if (res.ok) {
        setCart(await res.json());
      }
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const checkout = useCallback(async (): Promise<Order | null> => {
    if (!sessionId) return null;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/checkout`, {
        method: "POST",
        headers: { "X-Session-Id": sessionId },
      });
      if (!res.ok) return null;
      const order: Order = await res.json();
      setCart(emptyCart(sessionId));
      await refreshOrders();
      return order;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, refreshOrders]);

  const syncCartFromAgent = useCallback((nextCart: CartState) => {
    setCart(nextCart);
  }, []);

  return (
    <CartContext.Provider
      value={{
        sessionId,
        cart,
        orders,
        isLoading,
        addToCart,
        removeFromCart,
        clearCart,
        checkout,
        refreshCart,
        refreshOrders,
        syncCartFromAgent,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return ctx;
}

"use client";

import React, { useState } from "react";
import { Minus, Package, Plus, ShoppingBag, Trash2, X } from "lucide-react";
import { useCart } from "@/context/CartContext";

interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function CartDrawer({ open, onClose }: CartDrawerProps) {
  const { cart, orders, isLoading, addToCart, removeFromCart, clearCart, checkout } = useCart();
  const [tab, setTab] = useState<"cart" | "orders">("cart");
  const [checkoutNotice, setCheckoutNotice] = useState<string | null>(null);

  if (!open) return null;

  const handleCheckout = async () => {
    const order = await checkout();
    if (order) {
      setCheckoutNotice(`Order #${order.order_id} confirmed ($${order.total_amount.toFixed(2)})`);
      setTab("orders");
      setTimeout(() => setCheckoutNotice(null), 4000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTab("cart")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                tab === "cart"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <ShoppingBag className="h-4 w-4" />
              Cart ({cart.total_items})
            </button>
            <button
              type="button"
              onClick={() => setTab("orders")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                tab === "orders"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <Package className="h-4 w-4" />
              Orders ({orders.length})
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {checkoutNotice && (
          <div className="mx-5 mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
            {checkoutNotice}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-5">
          {tab === "cart" ? (
            cart.items.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center text-slate-400">
                <ShoppingBag className="mb-2 h-10 w-10 stroke-1" />
                <p className="text-sm font-medium text-slate-600">Your cart is empty</p>
                <p className="mt-1 text-xs">Ask the agent to find products or add items directly.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {cart.items.map((item) => (
                  <div
                    key={item.product_id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{item.name}</p>
                      <p className="text-xs text-slate-500">
                        ${item.price.toFixed(2)} each · Subtotal ${item.subtotal.toFixed(2)}
                      </p>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => removeFromCart(item.product_id, 1)}
                        className="rounded-md border border-slate-200 p-1 text-slate-600 hover:bg-slate-100"
                      >
                        <Minus className="h-3.5 w-3.5" />
                      </button>
                      <span className="w-6 text-center text-xs font-semibold">{item.qty}</span>
                      <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => addToCart(item.product_id, 1)}
                        className="rounded-md border border-slate-200 p-1 text-slate-600 hover:bg-slate-100"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => removeFromCart(item.product_id)}
                        className="ml-1 rounded-md p-1 text-rose-500 hover:bg-rose-50"
                        title="Remove item"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : orders.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-400">
              <Package className="mb-2 h-10 w-10 stroke-1" />
              <p className="text-sm font-medium text-slate-600">No orders yet</p>
              <p className="mt-1 text-xs">Completed checkouts for this session appear here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {orders.map((order) => (
                <div key={order.order_id} className="rounded-xl border border-slate-200 p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-900">
                      Order #{order.order_id}
                    </span>
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                      {order.status}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {new Date(order.created_at).toLocaleString()}
                  </p>
                  <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
                    {order.items.map((oi) => (
                      <li key={oi.product_id} className="flex justify-between">
                        <span>
                          {oi.qty}× {oi.product_name}
                        </span>
                        <span>${(oi.unit_price * oi.qty).toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-2 flex justify-between border-t border-slate-100 pt-2 text-xs font-semibold text-slate-900">
                    <span>Total</span>
                    <span>${order.total_amount.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {tab === "cart" && cart.items.length > 0 && (
          <div className="border-t border-slate-200 bg-slate-50 p-5">
            <div className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-900">
              <span>Total</span>
              <span>${cart.total_amount.toFixed(2)}</span>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={isLoading}
                onClick={clearCart}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                Clear
              </button>
              <button
                type="button"
                disabled={isLoading}
                onClick={handleCheckout}
                className="flex-1 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
              >
                Checkout Now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

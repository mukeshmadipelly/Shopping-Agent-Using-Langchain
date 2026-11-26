"use client";

import React, { useState } from "react";
import { Leaf, Plus, Star } from "lucide-react";
import { useCart } from "@/context/CartContext";
import type { Product } from "@/types/shop";

const FALLBACK_SVG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23f1f5f9'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-family='sans-serif' font-size='16'%3EProduct Image%3C/text%3E%3C/svg%3E";

export function ProductCard({ product }: { product: Product }) {
  const { addToCart, isLoading } = useCart();
  const [imgSrc, setImgSrc] = useState(product.image_url || FALLBACK_SVG);
  const [added, setAdded] = useState(false);

  const handleAdd = async () => {
    await addToCart(product.id, 1);
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  };

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="relative h-32 w-full bg-slate-100">
        <img
          src={imgSrc}
          alt={product.name}
          onError={() => setImgSrc(FALLBACK_SVG)}
          className="h-full w-full object-cover"
        />
        {product.is_organic && (
          <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-emerald-600/90 px-2 py-0.5 text-[11px] font-medium text-white">
            <Leaf className="h-3 w-3" />
            Organic
          </span>
        )}
        <span className="absolute right-2 top-2 rounded-md bg-slate-900/75 px-1.5 py-0.5 text-[10px] font-medium text-white">
          ID:{product.id}
        </span>
      </div>

      <div className="flex flex-1 flex-col justify-between p-3">
        <div>
          <div className="flex items-start justify-between gap-2">
            <h4 className="line-clamp-1 text-sm font-semibold text-slate-900">
              {product.name}
            </h4>
            <span className="shrink-0 text-sm font-bold text-slate-900">
              ${product.price.toFixed(2)}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-xs text-slate-500">
            {product.description}
          </p>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-amber-600">
            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
            <span className="font-medium text-slate-700">
              {product.average_rating.toFixed(1)}
            </span>
            <span className="text-slate-400">({product.review_count})</span>
          </div>

          <button
            type="button"
            onClick={handleAdd}
            disabled={isLoading}
            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
            {added ? "Added" : "Add"}
          </button>
        </div>
      </div>
    </div>
  );
}

export interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
  description: string;
  is_organic: boolean;
  image_url: string;
  average_rating: number;
  review_count: number;
}

export interface CartItem {
  product_id: number;
  name: string;
  category: string;
  price: number;
  qty: number;
  subtotal: number;
  is_organic: boolean;
  image_url: string;
}

export interface CartState {
  session_id: string;
  items: CartItem[];
  total_items: number;
  total_amount: number;
}

export interface OrderItem {
  product_id: number;
  product_name: string;
  unit_price: number;
  qty: number;
}

export interface Order {
  order_id: number;
  total_amount: number;
  status: string;
  created_at: string;
  items: OrderItem[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  imagePreview?: string;
  products?: Product[];
}

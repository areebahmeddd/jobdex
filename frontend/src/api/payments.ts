import { apiPost } from "./client";

export type OrderResponse = {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
};

export type VerifyResponse = {
  status: string;
  payment_id: string;
};

export function createOrder(amount: number): Promise<OrderResponse> {
  return apiPost<OrderResponse>("/payments/orders", { amount });
}

export function verifyPayment(payload: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}): Promise<VerifyResponse> {
  return apiPost<VerifyResponse>("/payments/verify", payload);
}

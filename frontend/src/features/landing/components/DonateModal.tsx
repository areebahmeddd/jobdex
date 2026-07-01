import { createOrder, verifyPayment } from "@/api/payments";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";

const FALLBACK_UPI = "https://razorpay.me/@1mindlabs";

const TIERS = [
  { emoji: "🍵", label: "Kadak Chai", amount: 10, desc: "Shukriya yaar" },
  { emoji: "☕", label: "Filter Coffee", amount: 50, desc: "Good vibes only" },
  {
    emoji: "🥭",
    label: "Mango Lassi",
    amount: 100,
    desc: "That's really sweet",
  },
  { emoji: "🥛", label: "Doodh Peda", amount: 500, desc: "Party banti hai" },
  {
    emoji: "🍫",
    label: "Hot Chocolate",
    amount: 1000,
    desc: "Absolute legend",
  },
];

interface DonateModalProps {
  open: boolean;
  onClose: () => void;
}

export function DonateModal({ open, onClose }: DonateModalProps) {
  const [loadingAmount, setLoadingAmount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDonate(amount: number) {
    setError(null);
    setLoadingAmount(amount);

    try {
      const {
        order_id,
        amount: orderAmount,
        currency,
        key_id,
      } = await createOrder(amount);

      await new Promise<void>((resolve, reject) => {
        const options = {
          key: key_id,
          amount: orderAmount,
          currency,
          name: "JobDex",
          description: "Support the project",
          order_id,
          modal: {
            ondismiss: () => reject(new Error("dismissed")),
          },
          handler: async (response: {
            razorpay_payment_id: string;
            razorpay_order_id: string;
            razorpay_signature: string;
          }) => {
            try {
              await verifyPayment({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              });
              resolve();
            } catch (err) {
              reject(err);
            }
          },
        };

        const rzp = new (
          window as unknown as {
            Razorpay: new (o: unknown) => {
              on: (e: string, cb: () => void) => void;
              open: () => void;
            };
          }
        ).Razorpay(options);
        rzp.on("payment.failed", () => reject(new Error("Payment failed.")));
        rzp.open();
      });

      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : null;
      if (message !== "dismissed") {
        setError(message ?? "Something went wrong. Please try again.");
      }
    } finally {
      setLoadingAmount(null);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setError(null);
          onClose();
        }
      }}
    >
      <DialogContent className="max-w-xs overflow-hidden p-0">
        <DialogHeader className="border-b border-black/8 px-5 py-4">
          <DialogTitle className="text-sm font-medium text-gray-950">
            Buy me a drink?
          </DialogTitle>
          <p className="mt-0.5 text-xs text-gray-500">
            Every bit keeps this running
          </p>
        </DialogHeader>

        <ul className="divide-y divide-black/6" role="list">
          {TIERS.map((tier) => (
            <li key={tier.amount}>
              <button
                type="button"
                onClick={() => handleDonate(tier.amount)}
                disabled={loadingAmount !== null}
                aria-label={`Donate ₹${tier.amount} for ${tier.label}`}
                className="group flex w-full cursor-pointer items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span
                  className="w-6 shrink-0 text-center text-base leading-none"
                  aria-hidden="true"
                >
                  {tier.emoji}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {tier.label}
                  </p>
                  <p className="text-xs text-gray-500">{tier.desc}</p>
                </div>
                <span className="shrink-0 rounded-full border border-black/10 px-2.5 py-0.5 text-xs font-medium text-gray-600 tabular-nums">
                  {loadingAmount === tier.amount ? "…" : `₹${tier.amount}`}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {error && (
          <p className="border-t border-black/6 px-5 py-2.5 text-xs text-red-500">
            {error} Or pay directly via UPI:{" "}
            <span className="font-medium text-gray-700">{FALLBACK_UPI}</span>
          </p>
        )}

        <div className="flex items-center justify-center gap-1.5 border-t border-black/6 px-5 py-2.5">
          <ShieldCheck
            className="size-3 shrink-0 text-gray-400"
            aria-hidden="true"
          />
          <span className="text-xs text-gray-500">Secured by Razorpay</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}

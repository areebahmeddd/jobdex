import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ShieldCheck } from "lucide-react";

const TIERS = [
  { emoji: "☕", label: "Chai", amount: 10, desc: "Shukriya yaar" },
  { emoji: "☕", label: "Coffee", amount: 50, desc: "Good vibes only" },
  { emoji: "🥭", label: "Shake", amount: 100, desc: "That's really sweet" },
  { emoji: "🥛", label: "Lassi", amount: 500, desc: "Party banti hai" },
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
  function handleDonate(amount: number) {
    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY,
      amount: amount * 100,
      currency: "INR",
      name: "JobDex",
      description: "Support the project",
      handler: () => onClose(),
    };
    new (window as any).Razorpay(options).open();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <DialogContent className="max-w-xs overflow-hidden p-0">
        <DialogHeader className="border-b border-black/8 px-5 py-4">
          <DialogTitle className="text-sm font-medium text-gray-950">
            Buy me a drink?
          </DialogTitle>
          <p className="mt-0.5 text-xs text-gray-400">
            Every bit keeps this running
          </p>
        </DialogHeader>

        <ul className="divide-y divide-black/6" role="list">
          {TIERS.map((tier) => (
            <li key={tier.amount}>
              <button
                type="button"
                onClick={() => handleDonate(tier.amount)}
                aria-label={`Donate ₹${tier.amount} for ${tier.label}`}
                className="group flex w-full cursor-pointer items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-black/5"
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
                  <p className="text-xs text-gray-400">{tier.desc}</p>
                </div>
                <span className="shrink-0 rounded-full border border-black/10 px-2.5 py-0.5 text-xs font-medium text-gray-600 tabular-nums">
                  ₹{tier.amount}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="flex items-center justify-center gap-1.5 px-5 py-2.5">
          <ShieldCheck
            className="size-3 shrink-0 text-gray-400"
            aria-hidden="true"
          />
          <span className="text-xs text-gray-400">Secured by Razorpay</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Check, Minus, Plus, Search, ShoppingCart, Trash2 } from "lucide-react";
import { toast } from "sonner";
import * as market from "@/services/marketplaceService";
import {
  Badge, Button, Card, EmptyNote, ErrorNote, Eyebrow, PageHeading, PageSkeleton, rupees,
} from "@/components/ui";

const STEPS = ["Delivery address", "Payment", "Confirmation"];

export default function Pharmacy() {
  const [catalog, setCatalog] = useState({ medicines: [], recommended: [], categories: ["All"] });
  const [cart, setCart] = useState(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [cartOpen, setCartOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [address, setAddress] = useState("");
  const [addressError, setAddressError] = useState("");
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadCatalog = useCallback(() => {
    setError("");
    market
      .fetchMedicines({ q: query, category })
      .then(setCatalog)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [query, category]);

  useEffect(() => {
    const id = setTimeout(loadCatalog, 220);
    return () => clearTimeout(id);
  }, [loadCatalog]);

  useEffect(() => {
    market.fetchCart().then(setCart).catch(() => {});
  }, []);

  async function handleAdd(medicine) {
    setBusy(medicine.id);
    try {
      setCart(await market.addToCart(medicine.id));
      toast.success(`${medicine.name} added`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function handleQuantity(item, quantity) {
    try {
      setCart(await market.updateCartItem(item.id, quantity));
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function handleRemove(item) {
    try {
      setCart(await market.removeCartItem(item.id));
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function handleCheckout() {
    setAddressError("");
    setBusy("checkout");
    try {
      const result = await market.checkout(address);
      setOrder(result);
      setCart(await market.fetchCart());
      setStep(2);
    } catch (err) {
      setAddressError(err.errors?.address || err.message);
      setStep(0);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <PageHeading
        eyebrow="Marketplace"
        title="Pharmacy"
        subtitle="Genuine medicines delivered from licensed pharmacies near you."
      >
        <Button variant="outline" onClick={() => setCartOpen(true)}>
          <ShoppingCart size={16} /> Cart
          {cart?.count > 0 && (
            <span
              className="num ml-1 rounded-full px-2 py-0.5 text-xs font-bold"
              style={{ backgroundColor: "var(--accent)", color: "var(--accent-fg)" }}
            >
              {cart.count}
            </span>
          )}
        </Button>
      </PageHeading>

      {catalog.recommended.length > 0 && (
        <section className="mb-8">
          <Eyebrow className="mb-3">Recommended for you</Eyebrow>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {catalog.recommended.map((medicine) => (
              <Card key={medicine.id} className="min-w-[230px] shrink-0 p-4">
                <h3 className="font-bold">{medicine.name}</h3>
                <p className="mt-0.5 text-sm" style={{ color: "var(--ink-faint)" }}>
                  {medicine.genericSalt}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="num font-bold">{rupees(medicine.price)}</span>
                  <Button size="sm" disabled={busy === medicine.id} onClick={() => handleAdd(medicine)}>
                    Add
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      <div className="mb-6 flex flex-col gap-4">
        <div className="relative">
          <Search
            size={16}
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2"
            style={{ color: "var(--ink-faint)" }}
            aria-hidden="true"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search medicines or salts"
            aria-label="Search medicines"
            className="w-full rounded-full py-2.5 pl-11 pr-4 text-sm outline-none"
            style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {catalog.categories.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className="rounded-full px-3.5 py-1.5 text-sm font-semibold"
              style={{
                backgroundColor: item === category ? "var(--primary)" : "var(--surface-2)",
                color: item === category ? "var(--primary-fg)" : "var(--ink-muted)",
                border: "1px solid var(--border)",
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <PageSkeleton rows={4} />
      ) : error ? (
        <ErrorNote message={error} onRetry={loadCatalog} />
      ) : catalog.medicines.length === 0 ? (
        <EmptyNote>Nothing matched that search.</EmptyNote>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {catalog.medicines.map((medicine) => (
            <Card key={medicine.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-lg font-bold">{medicine.name}</h3>
                {medicine.requiresPrescription && <Badge tone="rose">Rx</Badge>}
              </div>
              <p className="mt-0.5 text-sm" style={{ color: "var(--ink-faint)" }}>
                {medicine.genericSalt}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
                {medicine.packSize}
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--sage)" }}>
                Delivery: {medicine.deliveryEta}
              </p>
              <div className="mt-auto flex items-center justify-between pt-4">
                <span className="num text-xl font-bold">{rupees(medicine.price)}</span>
                <Button size="sm" disabled={busy === medicine.id} onClick={() => handleAdd(medicine)}>
                  {busy === medicine.id ? "Adding…" : "Add to cart"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {cartOpen && (
        <CartPanel
          cart={cart}
          step={step}
          steps={STEPS}
          address={address}
          addressError={addressError}
          order={order}
          busy={busy}
          onAddress={setAddress}
          onStep={setStep}
          onQuantity={handleQuantity}
          onRemove={handleRemove}
          onCheckout={handleCheckout}
          onClose={() => {
            setCartOpen(false);
            setStep(0);
            setOrder(null);
          }}
        />
      )}
    </div>
  );
}

function CartPanel({
  cart, step, steps, address, addressError, order, busy,
  onAddress, onStep, onQuantity, onRemove, onCheckout, onClose,
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      style={{ backgroundColor: "rgb(0 0 0 / 0.42)" }}
      onClick={onClose}
    >
      <aside
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-md flex-col overflow-y-auto p-6"
        style={{ backgroundColor: "var(--surface)", borderLeft: "1px solid var(--border)" }}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-xl">Your cart</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        <ol className="mt-5 flex gap-2">
          {steps.map((label, index) => (
            <li key={label} className="flex-1">
              <div
                className="h-1 rounded-full"
                style={{ backgroundColor: index <= step ? "var(--primary)" : "var(--surface-2)" }}
              />
              <p
                className="mt-1.5 text-xs"
                style={{ color: index <= step ? "var(--primary)" : "var(--ink-faint)" }}
              >
                {label}
              </p>
            </li>
          ))}
        </ol>

        {step === 2 && order ? (
          <div className="flex flex-1 flex-col items-center justify-center text-center">
            <span
              className="flex h-14 w-14 items-center justify-center rounded-full"
              style={{ backgroundColor: "var(--sage-bg)", color: "var(--sage)" }}
            >
              <Check size={26} />
            </span>
            <h3 className="mt-4 text-2xl">Order placed</h3>
            <p className="num mt-1 font-bold">{order.orderId}</p>
            <p className="mt-3 text-sm" style={{ color: "var(--ink-muted)" }}>
              {order.itemCount} item{order.itemCount > 1 ? "s" : ""} · {rupees(order.total)}
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--sage)" }}>
              Arriving {order.eta}
            </p>
            <p className="mt-3 max-w-xs text-sm" style={{ color: "var(--ink-faint)" }}>
              {order.address}
            </p>
            <Button className="mt-6" onClick={onClose}>
              Done
            </Button>
          </div>
        ) : !cart?.items?.length ? (
          <EmptyNote>Your cart is empty.</EmptyNote>
        ) : (
          <>
            <div className="mt-5 flex flex-col gap-3">
              {cart.items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-3 rounded-2xl p-3"
                  style={{ backgroundColor: "var(--surface-2)" }}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{item.medicine.name}</p>
                    <p className="num text-sm" style={{ color: "var(--ink-muted)" }}>
                      {rupees(item.medicine.price)} each
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <IconStep label="Decrease" onClick={() => onQuantity(item, item.quantity - 1)}>
                      <Minus size={13} />
                    </IconStep>
                    <span className="num w-6 text-center font-bold">{item.quantity}</span>
                    <IconStep label="Increase" onClick={() => onQuantity(item, item.quantity + 1)}>
                      <Plus size={13} />
                    </IconStep>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemove(item)}
                    aria-label={`Remove ${item.medicine.name}`}
                    style={{ color: "var(--ink-faint)" }}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>

            {step === 0 && (
              <div className="mt-6">
                <label htmlFor="address" className="label-eyebrow">
                  Delivery address
                </label>
                <textarea
                  id="address"
                  rows={3}
                  value={address}
                  onChange={(e) => onAddress(e.target.value)}
                  placeholder="Flat, building, area, city, pincode"
                  className="mt-1.5 w-full rounded-2xl px-4 py-3 text-sm outline-none"
                  style={{
                    backgroundColor: "var(--surface-2)",
                    border: `1px solid ${addressError ? "var(--rose)" : "var(--border)"}`,
                  }}
                />
                {addressError && (
                  <p className="mt-1 text-sm" style={{ color: "var(--rose)" }}>
                    {addressError}
                  </p>
                )}
              </div>
            )}

            {step === 1 && (
              <div className="mt-6 rounded-2xl p-4" style={{ backgroundColor: "var(--surface-2)" }}>
                <Eyebrow>Payment</Eyebrow>
                <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
                  Cash on delivery. Card and UPI arrive with the payments phase.
                </p>
                {cart.requiresPrescription && (
                  <p className="mt-3 text-sm" style={{ color: "var(--amber)" }}>
                    A pharmacist will verify your prescription before dispatch.
                  </p>
                )}
              </div>
            )}

            <div className="mt-6" style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <Row label="Subtotal" value={rupees(cart.subtotal)} />
              <Row label="Delivery" value={cart.delivery ? rupees(cart.delivery) : "Free"} />
              <Row label="Total" value={rupees(cart.total)} bold />
            </div>

            <Button
              className="mt-5 w-full"
              disabled={busy === "checkout"}
              onClick={() => (step === 0 ? onStep(1) : onCheckout())}
            >
              {busy === "checkout"
                ? "Placing order…"
                : step === 0
                  ? "Continue to payment"
                  : "Place order"}
            </Button>
            {step === 1 && (
              <Button variant="ghost" className="mt-2 w-full" onClick={() => onStep(0)}>
                Back
              </Button>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

function IconStep({ label, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="rounded-full p-1.5"
      style={{ border: "1px solid var(--border-strong)" }}
    >
      {children}
    </button>
  );
}

function Row({ label, value, bold }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm" style={{ color: "var(--ink-muted)" }}>
        {label}
      </span>
      <span className={bold ? "num text-lg font-bold" : "num text-sm"}>{value}</span>
    </div>
  );
}

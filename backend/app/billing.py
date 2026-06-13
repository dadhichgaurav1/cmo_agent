"""Stripe billing — Checkout, Customer Portal, and webhook-driven entitlement.

Webhooks are the source of truth: we never trust the checkout redirect. Subscription events write
`plan` / `subscription_status` / `current_period_end` onto the org row, which Phase 3 quotas read.
Gated on STRIPE_SECRET_KEY — when unset, `enabled()` is False and routes report disabled.
"""
from datetime import datetime, timezone
from typing import Optional

from app import config, db


def enabled() -> bool:
    return bool(config.STRIPE_SECRET_KEY)


def _stripe():
    if not enabled():
        return None
    import stripe
    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def _iso(ts) -> Optional[str]:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


def _plan_for_status(status: str) -> str:
    return "pro" if status in ("active", "trialing") else "free"


def ensure_customer(org_id: str, email: Optional[str]) -> Optional[str]:
    """Get-or-create the Stripe customer for an org; persists the id on the org row."""
    s = _stripe()
    if not s:
        return None
    cid = db.get_org(org_id).get("stripe_customer_id")
    if cid:
        return cid
    cust = s.Customer.create(email=email or None, metadata={"org_id": org_id})
    db.update_org(org_id, {"stripe_customer_id": cust.id})
    return cust.id


def create_checkout(org_id: str, email: Optional[str], success_url: str, cancel_url: str) -> Optional[str]:
    s = _stripe()
    if not s or not config.STRIPE_PRICE_PRO:
        return None
    cid = ensure_customer(org_id, email)
    sess = s.checkout.Session.create(
        mode="subscription",
        customer=cid,
        client_reference_id=org_id,
        line_items=[{"price": config.STRIPE_PRICE_PRO, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
    )
    return sess.url


def create_portal(org_id: str, return_url: str) -> Optional[str]:
    s = _stripe()
    if not s:
        return None
    cid = db.get_org(org_id).get("stripe_customer_id")
    if not cid:
        return None
    sess = s.billing_portal.Session.create(customer=cid, return_url=return_url)
    return sess.url


def handle_event(payload: bytes, sig: str) -> dict:
    """Verify + apply a Stripe webhook event. Raises on signature/parse failure."""
    s = _stripe()
    if not s:
        return {"ok": False, "reason": "billing disabled"}
    event = s.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        org_id = obj.get("client_reference_id") or db.org_id_for_customer(obj.get("customer"))
        fields = {
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("subscription"),
            "plan": "pro", "subscription_status": "active",
        }
        if obj.get("subscription"):
            sub = s.Subscription.retrieve(obj["subscription"])
            fields["subscription_status"] = sub["status"]
            fields["current_period_end"] = _iso(sub.get("current_period_end"))
            fields["plan"] = _plan_for_status(sub["status"])
        if org_id:
            db.update_org(org_id, fields)

    elif etype.startswith("customer.subscription."):
        org_id = db.org_id_for_customer(obj.get("customer"))
        status = obj.get("status", "")
        fields = {
            "subscription_status": status,
            "current_period_end": _iso(obj.get("current_period_end")),
            "stripe_subscription_id": obj.get("id"),
            "plan": _plan_for_status(status),
        }
        if etype.endswith(".deleted"):
            fields.update({"plan": "free", "subscription_status": "canceled"})
        if org_id:
            db.update_org(org_id, fields)

    elif etype == "invoice.payment_failed":
        org_id = db.org_id_for_customer(obj.get("customer"))
        if org_id:
            db.update_org(org_id, {"subscription_status": "past_due"})

    return {"ok": True, "type": etype}

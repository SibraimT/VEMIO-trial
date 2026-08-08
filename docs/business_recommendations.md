# VEMIO Case — Business Recommendations
**For:** Commercial and Trade Marketing team
**Based on:** demand forecasting, price sensitivity, and promotion analysis
for Desodorante 150 ml A (see `findings.md` for full technical detail)

---

## 1. Plan next year's summer promotion around the demand spike — don't
   wait to react to it

Every year, demand for this product jumps sharply in February–March. This
isn't random — it happens every year, and it lines up with when the summer
promotion typically runs. The risk is treating next year's forecast as a
"normal" number without accounting for a promotion that hasn't been
scheduled yet: a forecast built without knowing a promotion is coming will
understate demand, which can mean running out of stock right when demand is
highest.

**What to do:** decide the summer promotion calendar and discount level
before generating next quarter's demand forecast, and share it with
planning so the forecast reflects reality, not a "no promotion" scenario.

---

## 2. The summer promotion is profitable — but the discount is deeper than
   it needs to be

This is good news with a catch. The summer promotion genuinely sells extra
units that wouldn't have sold otherwise, and those extra units are
profitable. The problem is that the discount is deep enough that it also
gets applied to sales that would have happened anyway, even without a
promotion — and that part is pure lost margin, not incremental sales.

**What to do:** test a shallower discount on the next run of this
promotion. Based on how customers have responded to price changes
historically, a smaller discount should still trigger a meaningful demand
increase, while giving up much less margin on sales that didn't need a
discount to happen.

---

## 3. The end-of-quarter promotion is losing money — not just cutting into
   margin, actually losing money on every extra unit sold

This one is different from the summer promotion, and more serious. When we
isolate just the extra units this promotion generates (the sales that
wouldn't have happened without it), those units are being sold at a loss —
not just thin margin, an actual loss per unit. This means the more this
promotion "succeeds" at driving volume, the more money it loses.

**What to do:** this promotion should not run again in its current form.
Either cut the discount substantially or redesign it — running it as-is is
not a margin optimization problem, it's a structural loss.

---

## 4. Product costs have gone up — but promotional discounts haven't been
   adjusted to reflect that

Over the last two years, the cost to acquire this product has risen by
roughly 10%. Promotional discounts, however, appear to still be set based
on older cost levels. That gap is likely showing up across other
promotions too, not just the two analyzed here — meaning there could be
more unnoticed margin erosion happening across the promotion calendar.

**What to do:** before approving any promotion's discount level, check it
against *current* product cost, not the cost from when the discount
tier was originally set. This is likely the fastest, lowest-effort fix
available — it doesn't require new tools, just an updated cost check in
the approval process.

---

## 5. Use the demand forecast as a starting point, and adjust it when a
   promotion is planned

The current forecasting tool assumes no new promotions unless it's told
otherwise. That's a reasonable default, but it means any forecast covering
a period where a promotion is planned will likely be too low — the tool
simply doesn't know about it yet.

**What to do:** whenever a promotion is planned for an upcoming forecast
period, flag it so the forecast can be adjusted — either manually, or by
re-running the model with the planned promotion's discount level included.
Treat the raw forecast number as a baseline to adjust, not a final answer,
whenever a promotion is on the calendar.
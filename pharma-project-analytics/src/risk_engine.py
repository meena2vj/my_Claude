"""Deterministic risk classification for pharma inventory batches.

Expiry Status, Stock Status, and the Critical-Risk combination rule are
defined by `.claude/skills/pharma-risk/SKILL.md` and must not deviate
from it. Risk_Score, Risk_Level, and Recommended_Action are a Phase 2
extension layered on top of those same rules, documented below, so every
number is traceable back to a rule rather than an opaque score (per
docs/GOVERNANCE.md "Calculation Transparency").

No machine learning or LLM is used anywhere in this module. All inputs
are treated defensively: a missing or invalid value never causes a
crash and is never guessed at — it produces an explicit "UNKNOWN"/
"INVALID" classification instead (per docs/GOVERNANCE.md "never attempt
to 'guess' or silently repair malformed data").

--------------------------------------------------------------------
Expiry Status (from pharma-risk SKILL.md, boundaries inclusive as shown)
--------------------------------------------------------------------
    days_to_expiry < 0                    -> EXPIRED
    0 <= days_to_expiry <= 30              -> EXPIRING_SOON
    days_to_expiry > 30                    -> SAFE
    Expiry_Date missing/unparseable        -> UNKNOWN

------------------------------------------------------
Stock Status (from pharma-risk SKILL.md)
------------------------------------------------------
    Current_Stock missing/unparseable/negative       -> INVALID
    Reorder_Level or Maximum_Stock missing/unparseable -> UNKNOWN
    Current_Stock < Reorder_Level                     -> LOW_STOCK
    Current_Stock > Maximum_Stock                     -> OVERSTOCK
    otherwise                                         -> NORMAL

------------------------------------------------------
Critical Risk flag (from pharma-risk SKILL.md)
------------------------------------------------------
    True when Critical_Medicine is Yes AND
    (Expiry_Status == EXPIRED OR Stock_Status == LOW_STOCK)

------------------------------------------------------
Risk_Score (Phase 2 extension, 0-100, additive point system)
------------------------------------------------------
    Expiry contribution:
        EXPIRED         -> 50
        EXPIRING_SOON   -> 30
        UNKNOWN         -> 20  (data issue -> needs review, not ignored)
        SAFE            -> 0

    Stock contribution:
        LOW_STOCK       -> 30
        OVERSTOCK       -> 15
        INVALID/UNKNOWN -> 20  (data issue -> needs review, not ignored)
        NORMAL          -> 0

    Critical-medicine bonus:
        +30 if is_critical_risk() is True (see Critical Risk flag above),
        else +0.

    Total = expiry contribution + stock contribution + critical bonus,
    capped at 100.

------------------------------------------------------
Risk_Level thresholds (Phase 2 extension)
------------------------------------------------------
    Risk_Score >= 60   -> Critical
    40 <= Risk_Score < 60 -> High
    20 <= Risk_Score < 40 -> Medium
    Risk_Score < 20    -> Low

These thresholds are chosen so that the pharma-risk SKILL.md Critical
Risk flag always lands in the "Critical" level (EXPIRED+critical = 80,
LOW_STOCK+critical = 60), while a single non-critical issue (EXPIRED
alone = 50, LOW_STOCK/EXPIRING_SOON alone = 30) lands in High/Medium.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from .parsing import to_date, to_float, to_yes_no

EXPIRED = "EXPIRED"
EXPIRING_SOON = "EXPIRING_SOON"
SAFE = "SAFE"
EXPIRY_UNKNOWN = "UNKNOWN"

LOW_STOCK = "LOW_STOCK"
OVERSTOCK = "OVERSTOCK"
NORMAL = "NORMAL"
STOCK_INVALID = "INVALID"
STOCK_UNKNOWN = "UNKNOWN"

RISK_CRITICAL = "Critical"
RISK_HIGH = "High"
RISK_MEDIUM = "Medium"
RISK_LOW = "Low"

EXPIRING_SOON_WINDOW_DAYS = 30

EXPIRY_SCORE = {
    EXPIRED: 50,
    EXPIRING_SOON: 30,
    EXPIRY_UNKNOWN: 20,
    SAFE: 0,
}

STOCK_SCORE = {
    LOW_STOCK: 30,
    OVERSTOCK: 15,
    STOCK_INVALID: 20,
    STOCK_UNKNOWN: 20,
    NORMAL: 0,
}

CRITICAL_BONUS = 30
MAX_RISK_SCORE = 100


def compute_days_to_expiry(
    expiry_date, reference_date: Optional[date] = None
) -> Optional[int]:
    """Days from `reference_date` (default: today) to `expiry_date`.

    Negative means already expired. Returns None if `expiry_date` is
    missing or unparseable.
    """
    parsed = to_date(expiry_date) if not isinstance(expiry_date, date) else expiry_date
    if parsed is None:
        return None
    ref = reference_date if reference_date is not None else date.today()
    return (parsed - ref).days


def classify_expiry_status(days_to_expiry: Optional[int]) -> str:
    """Classify Expiry Status from Days_To_Expiry per pharma-risk SKILL.md."""
    if days_to_expiry is None:
        return EXPIRY_UNKNOWN
    if days_to_expiry < 0:
        return EXPIRED
    if days_to_expiry <= EXPIRING_SOON_WINDOW_DAYS:
        return EXPIRING_SOON
    return SAFE


def classify_stock_status(current_stock, reorder_level, maximum_stock) -> str:
    """Classify Stock Status per pharma-risk SKILL.md, with explicit
    INVALID/UNKNOWN outcomes for missing or malformed inputs.
    """
    stock = to_float(current_stock)
    if stock is None or stock < 0:
        return STOCK_INVALID

    reorder = to_float(reorder_level)
    maximum = to_float(maximum_stock)
    if reorder is None or maximum is None:
        return STOCK_UNKNOWN

    if stock < reorder:
        return LOW_STOCK
    if stock > maximum:
        return OVERSTOCK
    return NORMAL


def compute_inventory_value(current_stock, unit_price) -> Optional[float]:
    """Current_Stock * Unit_Price. Returns None if either value is
    missing/unparseable or Current_Stock is negative (an invalid
    physical quantity cannot be priced).
    """
    stock = to_float(current_stock)
    price = to_float(unit_price)
    if stock is None or price is None or stock < 0 or price < 0:
        return None
    return round(stock * price, 2)


def is_critical_risk(
    expiry_status: str, stock_status: str, is_critical_medicine: Optional[bool]
) -> bool:
    """Critical Risk flag per pharma-risk SKILL.md: the medicine is marked
    critical AND (expired OR low stock).
    """
    if not is_critical_medicine:
        return False
    return expiry_status == EXPIRED or stock_status == LOW_STOCK


def compute_risk_score(
    expiry_status: str, stock_status: str, is_critical_medicine: Optional[bool]
) -> int:
    """Additive 0-100 Risk_Score. See module docstring for the point table."""
    score = EXPIRY_SCORE.get(expiry_status, EXPIRY_SCORE[EXPIRY_UNKNOWN])
    score += STOCK_SCORE.get(stock_status, STOCK_SCORE[STOCK_UNKNOWN])
    if is_critical_risk(expiry_status, stock_status, is_critical_medicine):
        score += CRITICAL_BONUS
    return min(score, MAX_RISK_SCORE)


def classify_risk_level(risk_score: int) -> str:
    """Map Risk_Score to a Risk_Level. See module docstring for thresholds."""
    if risk_score >= 60:
        return RISK_CRITICAL
    if risk_score >= 40:
        return RISK_HIGH
    if risk_score >= 20:
        return RISK_MEDIUM
    return RISK_LOW


def recommend_action(
    expiry_status: str,
    stock_status: str,
    is_critical_medicine: Optional[bool],
) -> str:
    """Deterministic, human-readable next step for a batch. Multiple
    applicable actions are joined with '; '; a data-issue note always
    comes first since it should be resolved before acting on the
    classification that produced it.
    """
    actions: list[str] = []

    if expiry_status == EXPIRY_UNKNOWN:
        actions.append("Verify batch data - missing or invalid expiry date")
    if stock_status == STOCK_INVALID:
        actions.append("Verify batch data - missing or invalid current stock")
    elif stock_status == STOCK_UNKNOWN:
        actions.append("Verify batch data - missing reorder level or maximum stock")

    if expiry_status == EXPIRED:
        actions.append("Remove from inventory immediately - batch expired")
    elif expiry_status == EXPIRING_SOON:
        actions.append("Prioritize distribution or use before expiry (within 30 days)")

    if stock_status == LOW_STOCK:
        actions.append("Reorder stock - below reorder level")
    elif stock_status == OVERSTOCK:
        actions.append("Reduce future orders - stock exceeds maximum level")

    if is_critical_risk(expiry_status, stock_status, is_critical_medicine):
        actions.insert(0, "URGENT - flag for human review (critical medicine)")

    if not actions:
        actions.append("No action needed - monitor routinely")

    return "; ".join(actions)


def apply_risk_engine(
    df: pd.DataFrame, reference_date: Optional[date] = None
) -> pd.DataFrame:
    """Return a copy of `df` with the seven risk-engine columns appended:
    Days_To_Expiry, Expiry_Status, Stock_Status, Inventory_Value,
    Risk_Score, Risk_Level, Recommended_Action.

    `reference_date` defaults to today; tests should always pass a fixed
    date (per CLAUDE.md "no test may depend on ... system time drift").
    """
    result = df.copy()

    days_to_expiry = result["Expiry_Date"].apply(
        lambda v: compute_days_to_expiry(v, reference_date)
    )
    expiry_status = days_to_expiry.apply(classify_expiry_status)
    stock_status = result.apply(
        lambda row: classify_stock_status(
            row.get("Current_Stock"), row.get("Reorder_Level"), row.get("Maximum_Stock")
        ),
        axis=1,
    )
    inventory_value = result.apply(
        lambda row: compute_inventory_value(row.get("Current_Stock"), row.get("Unit_Price")),
        axis=1,
    )
    is_critical_medicine = result["Critical_Medicine"].apply(to_yes_no)

    risk_score = [
        compute_risk_score(exp, stock, crit)
        for exp, stock, crit in zip(expiry_status, stock_status, is_critical_medicine)
    ]
    risk_level = [classify_risk_level(score) for score in risk_score]
    recommended_action = [
        recommend_action(exp, stock, crit)
        for exp, stock, crit in zip(expiry_status, stock_status, is_critical_medicine)
    ]

    result["Days_To_Expiry"] = days_to_expiry
    result["Expiry_Status"] = expiry_status
    result["Stock_Status"] = stock_status
    result["Inventory_Value"] = inventory_value
    result["Risk_Score"] = risk_score
    result["Risk_Level"] = risk_level
    result["Recommended_Action"] = recommended_action

    return result

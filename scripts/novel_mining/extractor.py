"""Check quoted evidence without keeping a collection ledger."""


def validate_claims(text, claims):
    """Return structural/evidence errors; a match is not semantic approval.

    An unambiguous literal quotation needs no offset. Repeated quotations
    require explicit Unicode offsets relative to the selected text, [start,end).
    """
    if not isinstance(claims, list):
        raise ValueError("Input must be a JSON list of claims")
    errors = []
    for index, claim in enumerate(claims, 1):
        prefix = f"Claim {index}: "
        if not isinstance(claim, dict):
            errors.append(prefix + "expected an object")
            continue
        required = ("target_name", "category", "attribute", "value", "claim_type", "evidence_snippet")
        if any(not isinstance(claim.get(k), str) or not claim[k].strip() for k in required):
            errors.append(prefix + "missing a required text field")
            continue
        kind = claim["claim_type"]
        if kind not in ("旁白说明", "情节展示", "人物说法", "传闻", "否定/假设"):
            errors.append(prefix + "unknown claim type")
        if kind in ("人物说法", "传闻") and (
            not isinstance(claim.get("speaker"), str) or not claim["speaker"].strip()
        ):
            errors.append(prefix + "speaker attribution is required")
        quote = claim["evidence_snippet"]
        start, end = claim.get("evidence_start"), claim.get("evidence_end")
        if start is not None or end is not None:
            if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(text)):
                errors.append(prefix + "invalid evidence range")
            elif text[start:end] != quote:
                errors.append(prefix + "quotation differs from the selected text")
        elif text.count(quote) != 1:
            errors.append(prefix + "quotation must occur once; repeated quotations require offsets")
    return errors

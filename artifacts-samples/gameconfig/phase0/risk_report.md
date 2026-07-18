# Risk Report

## Balance & Consistency Review
- Issue: base_attack does not match the requirement and exceeds beginner policy
- Severity: high
- Evidence: `{"actual": 80, "required": 50, "recommended_range": [35, 55]}`
- Recommended range: `[35, 55]`
- Preferred fix: Set base_attack to the requested value 50.

## Balance & Consistency Review
- Issue: upgrade levels are not continuous
- Severity: high
- Evidence: `{"actual_levels": [1, 3], "expected_levels": [1, 2, 3]}`
- Recommended range: `[1, 2, 3]`
- Preferred fix: Create a local level 2 upgrade row and normalize all level costs.

## Balance & Consistency Review
- Issue: upgrade gold cost is too low for the recommended curve
- Severity: medium
- Evidence: `{"actual_gold_costs": [0, 0]}`
- Recommended range: `[100, 150, 200]`
- Preferred fix: Use the deterministic beginner curve 100, 150, 200.

## Risk Review
- Issue: beginner quest reward can be claimed repeatedly
- Severity: critical
- Evidence: `{"once_only": false}`
- Recommended range: `[true]`
- Preferred fix: Set reward_config.once_only to true.

## Risk Review
- Issue: configuration contains missing item references
- Severity: high
- Evidence: `[{"source": "Reference Checker Tool", "code": "missing_reference", "path": "upgrade_config[0].cost_items[1].item_id", "value": "item_refine_stone", "target": "item_config.item_id", "message": "'item_refine_stone' does not exist in item_config.item_id."}]`
- Recommended range: `["all referenced item_id values exist in item_config"]`
- Preferred fix: Add a minimal item_refine_stone item definition.

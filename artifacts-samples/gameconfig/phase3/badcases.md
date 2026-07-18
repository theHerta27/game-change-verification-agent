# Phase 3 Badcases

## Badcase 1
- Sample: `duplicate_reward_hardcase`
- Stage: `final_validation`
- Reason: sample remains unresolved after benchmark flow
- Detail: `{"sample_id": "duplicate_reward_hardcase", "stage": "final_validation", "reason": "sample remains unresolved after benchmark flow", "schema_errors": [], "reference_errors": [], "rule_errors": [{"source": "Rule Engine Tool", "code": "duplicate_id", "path": "reward_config", "message": "Duplicate reward_id: reward_weapon_moon_saber_dup"}]}`

## Badcase 2
- Sample: `skill_damage_optional_config`
- Stage: `schema_validation`
- Reason: initial schema validation failed
- Detail: `{"sample_id": "skill_damage_optional_config", "stage": "schema_validation", "reason": "initial schema validation failed", "errors": [{"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].display_name", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].damage", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].cooldown", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].range", "message": "Required field is missing."}]}`

## Badcase 3
- Sample: `skill_damage_optional_config`
- Stage: `final_validation`
- Reason: sample remains unresolved after benchmark flow
- Detail: `{"sample_id": "skill_damage_optional_config", "stage": "final_validation", "reason": "sample remains unresolved after benchmark flow", "schema_errors": [{"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].display_name", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].damage", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].cooldown", "message": "Required field is missing."}, {"source": "Schema Validator Tool", "code": "missing_field", "path": "skill_config[0].range", "message": "Required field is missing."}], "reference_errors": [], "rule_errors": []}`

## Badcase 4
- Sample: `missing_reward_reference`
- Stage: `final_validation`
- Reason: sample remains unresolved after benchmark flow
- Detail: `{"sample_id": "missing_reward_reference", "stage": "final_validation", "reason": "sample remains unresolved after benchmark flow", "schema_errors": [], "reference_errors": [{"source": "Reference Checker Tool", "code": "missing_reference", "path": "reward_config[0].reward_item_id", "value": "item_missing_reward", "target": "item_config.item_id", "message": "'item_missing_reward' does not exist in item_config.item_id."}], "rule_errors": []}`

## Badcase 5
- Sample: `dirty_schema_hardcase`
- Stage: `schema_validation`
- Reason: initial schema validation failed
- Detail: `{"sample_id": "dirty_schema_hardcase", "stage": "schema_validation", "reason": "initial schema validation failed", "errors": [{"source": "Schema Validator Tool", "code": "invalid_type", "path": "upgrade_config[0]", "message": "Expected object, got str."}]}`

## Badcase 6
- Sample: `dirty_schema_hardcase`
- Stage: `final_validation`
- Reason: sample remains unresolved after benchmark flow
- Detail: `{"sample_id": "dirty_schema_hardcase", "stage": "final_validation", "reason": "sample remains unresolved after benchmark flow", "schema_errors": [{"source": "Schema Validator Tool", "code": "invalid_type", "path": "upgrade_config[0]", "message": "Expected object, got str."}], "reference_errors": [], "rule_errors": []}`

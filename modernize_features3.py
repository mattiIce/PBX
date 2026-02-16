#!/usr/bin/env python3
"""
Third pass: fix all remaining missing annotations.
"""
import ast
import re
from pathlib import Path

# Explicit mapping of (filename, func_name, line_approx) -> return type
RETURN_TYPE_MAP = {
    # Return None functions (void)
    ("ai_call_routing.py", "_initialize_model"): "None",
    ("ai_call_routing.py", "_train_model"): "None",
    ("bi_integration.py", "create_custom_dataset"): "None",
    ("bi_integration.py", "schedule_export"): "None",
    ("call_quality_prediction_db.py", "save_metrics"): "None",
    ("call_quality_prediction_db.py", "save_prediction"): "None",
    ("call_quality_prediction_db.py", "save_alert"): "None",
    ("call_queue.py", "enqueue"): "None",
    ("call_recording_analytics.py", "_load_vosk_model"): "None",
    ("call_recording_analytics.py", "_process_vosk_audio"): "str",
    ("call_tagging.py", "_initialize_ml_classifier"): "None",
    ("call_tagging.py", "_initialize_spacy"): "None",
    ("callback_queue.py", "_initialize_schema"): "None",
    ("callback_queue.py", "_load_callbacks_from_database"): "None",
    ("cdr.py", "start_record"): "CDRRecord",
    ("cdr.py", "end_record"): "None",
    ("conference.py", "get_room"): "Any | None",
    ("conversational_ai.py", "_initialize_nltk"): "None",
    ("conversational_ai.py", "_build_response_handlers"): "None",
    ("conversational_ai_db.py", "save_message"): "None",
    ("conversational_ai_db.py", "save_intent"): "None",
    ("crm_integration.py", "_add_to_cache"): "None",
    ("crm_integration.py", "trigger_screen_pop"): "None",
    ("dnd_scheduling.py", "_check_all_rules"): "None",
    ("dns_srv_failover.py", "mark_server_failed"): "None",
    ("dns_srv_failover.py", "mark_server_recovered"): "None",
    ("emergency_notification.py", "_send_call_notification"): "None",
    ("emergency_notification.py", "_send_email_notification"): "None",
    ("emergency_notification.py", "_send_sms_notification"): "None",
    ("emergency_notification.py", "_send_sms_twilio"): "None",
    ("emergency_notification.py", "_send_sms_aws"): "None",
    ("emergency_notification.py", "on_911_call"): "None",
    ("extensions.py", "_load_extensions"): "None",
    ("find_me_follow_me.py", "_initialize_schema"): "None",
    ("find_me_follow_me.py", "_load_from_database"): "None",
    ("geographic_redundancy.py", "_trigger_failover"): "None",
    ("ilbc_codec.py", "create_encoder"): "Any",
    ("ilbc_codec.py", "create_decoder"): "Any",
    ("karis_law.py", "_trigger_emergency_notification"): "None",
    ("mfa.py", "_update_last_used"): "None",
    ("mobile_push.py", "_initialize_schema"): "None",
    ("mobile_push.py", "_load_devices_from_database"): "None",
    ("mobile_push.py", "_save_notification_to_database"): "None",
    ("opus_codec.py", "create_encoder"): "Any",
    ("opus_codec.py", "create_decoder"): "Any",
    ("phone_book.py", "_create_table"): "None",
    ("phone_book.py", "_load_from_database"): "None",
    ("phone_provisioning.py", "_load_devices_from_database"): "None",
    ("phone_provisioning.py", "_load_builtin_templates"): "None",
    ("phone_provisioning.py", "_add_request_log"): "None",
    ("predictive_dialing.py", "start_campaign"): "dict",
    ("predictive_dialing.py", "pause_campaign"): "dict",
    ("predictive_dialing.py", "stop_campaign"): "dict",
    ("predictive_dialing_db.py", "save_attempt"): "None",
    ("presence.py", "register_user"): "None",
    ("presence.py", "check_auto_status"): "None",
    ("recording_announcements.py", "_initialize_schema"): "None",
    ("recording_announcements.py", "_log_announcement"): "None",
    ("sip_trunk.py", "_update_health_status"): "None",
    ("sip_trunk.py", "start_health_monitoring"): "None",
    ("sip_trunk.py", "_health_monitoring_loop"): "None",
    ("sip_trunk.py", "_perform_health_checks"): "None",
    ("sip_trunk.py", "_handle_trunk_failure"): "None",
    ("speex_codec.py", "create_encoder"): "Any",
    ("speex_codec.py", "create_decoder"): "Any",
    ("stir_shaken.py", "add_stir_shaken_to_invite"): "None",
    ("voice_biometrics_db.py", "save_verification"): "None",
    ("voice_biometrics_db.py", "save_fraud_detection"): "None",
    ("voicemail.py", "_load_messages"): "None",
    ("webhooks.py", "_deliver_webhook"): "None",
    ("webhooks.py", "trigger_event"): "None",
}

# Explicit param type mappings
PARAM_TYPE_MAP = {
    ("auto_attendant.py", "_navigate_to_submenu", "submenu_id"): "str",
    ("phone_provisioning.py", "_add_request_log", "request_log"): "dict",
    ("statistics.py", "__init__", "cdr_system"): "Any",
}


def process_file(filepath: Path) -> tuple[bool, int]:
    """Process a single file."""
    source = filepath.read_text()
    source_lines = source.split("\n")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False, 0

    changes = []
    annotation_count = 0
    needs_any = False

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_name = node.name
        has_return = node.returns is not None

        # Check if this function needs a return annotation
        key = (filepath.name, func_name)
        return_type = RETURN_TYPE_MAP.get(key) if not has_return else None

        # Check if this function has missing param annotations
        missing_params = {}
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is not None:
                continue
            param_key = (filepath.name, func_name, arg.arg)
            if param_key in PARAM_TYPE_MAP:
                missing_params[arg.arg] = PARAM_TYPE_MAP[param_key]

        if return_type is None and not missing_params:
            continue

        if return_type and "Any" in return_type:
            needs_any = True
        for t in missing_params.values():
            if "Any" in t:
                needs_any = True

        # Get function signature lines
        func_line_start = node.lineno - 1
        sig_lines = []
        line_idx = func_line_start
        paren_depth = 0
        found_close = False

        while line_idx < len(source_lines):
            line = source_lines[line_idx]
            sig_lines.append(line)

            for ch in line:
                if ch == "(":
                    paren_depth += 1
                elif ch == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        found_close = True

            if found_close:
                break
            line_idx += 1

        sig_text = "\n".join(sig_lines)
        modified = False

        # Apply param annotations
        for param_name, type_hint in missing_params.items():
            already_annotated = re.search(rf"\b{re.escape(param_name)}\s*:", sig_text)
            if already_annotated:
                continue

            default_pattern = rf"\b{re.escape(param_name)}\s*=\s*None\b"
            has_none_default = re.search(default_pattern, sig_text)
            effective_type = type_hint
            if has_none_default and "None" not in type_hint:
                effective_type = f"{type_hint} | None"

            pattern1 = rf"(\b{re.escape(param_name)}\s*)(=)"
            new_sig, n = re.subn(pattern1, rf"\1: {effective_type} \2", sig_text, count=1)
            if n > 0:
                sig_text = new_sig
                modified = True
                annotation_count += 1
                continue

            pattern2 = rf"(\b{re.escape(param_name)}\s*)([,\)])"
            new_sig, n = re.subn(pattern2, rf"\1: {effective_type}\2", sig_text, count=1)
            if n > 0:
                sig_text = new_sig
                modified = True
                annotation_count += 1

        # Apply return annotation
        if return_type and " -> " not in sig_text:
            sig_text = re.sub(r"\)\s*:", f") -> {return_type}:", sig_text, count=1)
            modified = True
            annotation_count += 1

        if modified:
            changes.append((func_line_start, line_idx, sig_text.split("\n")))

    if not changes:
        return False, 0

    # Apply changes in reverse order
    changes.sort(key=lambda x: x[0], reverse=True)
    for start_line, end_line, new_lines in changes:
        source_lines[start_line:end_line + 1] = new_lines

    new_source = "\n".join(source_lines)

    # Add Any import if needed
    if needs_any and "Any" not in new_source.split("import")[0] if "import" in new_source else True:
        if "from typing import" in new_source:
            if "Any" not in new_source:
                # Add Any to existing import
                new_source = re.sub(
                    r"(from typing import\s+)(.*)",
                    lambda m: f"{m.group(1)}Any, {m.group(2)}" if "Any" not in m.group(2) else m.group(0),
                    new_source,
                    count=1
                )
        elif needs_any:
            # Check if Any is really used in annotations
            lines = new_source.split("\n")
            import_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")):
                    import_idx = i + 1
                elif line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""') and import_idx > 0:
                    break
            lines.insert(import_idx, "from typing import Any")
            new_source = "\n".join(lines)

    filepath.write_text(new_source)
    return True, annotation_count


def main():
    features_dir = Path("pbx/features")
    total_changed = 0
    total_annotations = 0

    for py_file in sorted(features_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        changed, count = process_file(py_file)
        if changed:
            total_changed += 1
            total_annotations += count
            print(f"  {py_file.name}: +{count} annotations")

    print(f"\nTotal: {total_changed} files changed, {total_annotations} annotations added")


if __name__ == "__main__":
    main()

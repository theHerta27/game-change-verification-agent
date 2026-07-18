from agent_service.tools.diff_parser import parse_unified_diff


def test_diff_parser_extracts_file_and_added_line_numbers():
    diff = """diff --git a/service/client.go b/service/client.go
--- a/service/client.go
+++ b/service/client.go
@@ -1,3 +1,5 @@
 package service
+func added() {}
+func added2() {}
"""
    parsed = parse_unified_diff(diff)

    assert parsed.files[0].new_path == "service/client.go"
    added_lines = [
        line.new_line_number
        for hunk in parsed.files[0].hunks
        for line in hunk.lines
        if line.line_type == "added"
    ]
    assert added_lines == [2, 3]


from oteltest.private import get_next_json_file, save_telemetry_json


def test_get_next_json_file(tmp_path):
    module_name = "my_module_name"
    path_to_dir = str(tmp_path)

    next_file = get_next_json_file(path_to_dir, module_name)
    assert "my_module_name.0.json" == next_file

    save_telemetry_json(path_to_dir, next_file, "")

    next_file = get_next_json_file(path_to_dir, module_name)
    assert "my_module_name.1.json" == next_file

    save_telemetry_json(path_to_dir, next_file, "[1]")

    next_file = get_next_json_file(path_to_dir, module_name)
    assert "my_module_name.2.json" == next_file

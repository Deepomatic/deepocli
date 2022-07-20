from deepomatic.cli.cmds.utils import CommandResult


TESTS = (
    {
        "operation": "operation_1",
        "resource_name": "resource_1",
        "data": {"field1": "value1", "field2": "value2", "id": "value_id"}
    },
    {
        "operation": "operation_1",
        "resource_name": "resource_1",
        "data": {"field1": "value1", "field2": "value2", "id": "value_id"},
        "fields_filter": ["field1", "field2"]
    },
    {
        "operation": "operation_1",
        "resource_name": "resource_1",
        "data": {"field1": "value1", "field2": "value2", "id": "value_id"},
        "extra": "extra_field=value_extra"
    }
)


class TestCommandResult():

    def test_common_usage(no_error_logs):
        for test in TESTS:
            command_result = str(CommandResult(**test))
            assert command_result.startswith("[")
            assert test["operation"] in str(command_result)
            assert test["resource_name"] in str(command_result)
            if "extra" in test:
                assert test["extra"] in str(command_result)
            if "fields_filter" in test:
                for field in test["fields_filter"]:
                    assert "{}={}".format(field, test["data"][field]) in command_result
            else:
                assert "id={}".format(test["data"]["id"]) in command_result

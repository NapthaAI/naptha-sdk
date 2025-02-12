# Testing

## Configuring the tests

Choose whether you want to interact with a local Naptha node or a hosted Naptha node. For a local node, set ```NODE_URL=http://localhost:7001``` in the .env file. To use a hosted node, set ```NODE_URL=https://node.naptha.ai```.

## Running the tests

Run all tests for CLI commands:

```bash
pytest tests/test_cli.py
```

Run all tests involving CLI commands that interact with the Hub:

```bash
pytest tests/test_cli.py::TestNapthaCLI::test_hub_command
```

Run all tests involving CLI commands that create a module:

```bash
pytest tests/test_cli.py::TestNapthaCLI::test_create_module_command
```

Run all tests involving CLI commands that run a module:

```bash
pytest tests/test_cli.py::TestNapthaCLI::test_run_module_command
```

Run all tests involving CLI commands that run inference:

```bash
pytest tests/test_cli.py::TestNapthaCLI::test_storage_and_inference_command
```

## Running the tests with verbose output

For you can use the `--v --capture=no` flags to get more verbose output and capture output from the tests.
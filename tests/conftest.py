"""
Shared pytest configuration.

All tests mock external calls (HTTP, FTP, AI APIs) at method level.
config.json and secrets.json must exist in the project root — they are
always present in CI (created by the workflow) and locally for developers.
"""

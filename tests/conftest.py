import os

# Must be set before importing modules that instantiate core.config.settings.
os.environ.setdefault("FACELENS_API_KEY", "test-only-api-key-with-at-least-thirty-two-characters")

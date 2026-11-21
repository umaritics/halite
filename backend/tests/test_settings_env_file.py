"""Removing a redundant direct pin must preserve actual dotenv-backed settings."""
from config import Settings


def test_env_file_loads_quoted_values_and_typed_settings_after_dependency_cleanup(tmp_path, monkeypatch):
    for name in ('HALITE_API_KEY', 'MAINT_CONFIDENCE_THRESHOLD', 'BOOTSTRAP_ADMIN_NAME'):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / 'settings.env'
    path.write_text('HALITE_API_KEY="synthetic-test-key-from-env-file"\nMAINT_CONFIDENCE_THRESHOLD=0.83\nBOOTSTRAP_ADMIN_NAME="Synthetic Usman fixture"\n')
    settings = Settings(_env_file=path)
    assert settings.HALITE_API_KEY == 'synthetic-test-key-from-env-file'
    assert settings.MAINT_CONFIDENCE_THRESHOLD == .83
    assert settings.BOOTSTRAP_ADMIN_NAME == 'Synthetic Usman fixture'

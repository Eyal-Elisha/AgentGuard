from __future__ import annotations

import os
import unittest

from cryptography.fernet import Fernet

from backend.log_encryption import ENCRYPTED_VALUE_PREFIX, decrypt_text, encrypt_text


class LogEncryptionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._old_key = os.environ.get("AGENTGUARD_LOG_ENCRYPTION_KEY")

    def tearDown(self) -> None:
        if self._old_key is None:
            os.environ.pop("AGENTGUARD_LOG_ENCRYPTION_KEY", None)
        else:
            os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = self._old_key

    def test_encrypts_and_decrypts_text_without_plaintext_leak(self):
        os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")

        encrypted = encrypt_text("https://example.test/login")

        self.assertIsNotNone(encrypted)
        self.assertTrue(encrypted.startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertNotIn("example.test", encrypted)
        self.assertEqual(decrypt_text(encrypted), "https://example.test/login")

    def test_missing_key_fails_before_persisting_plaintext(self):
        os.environ.pop("AGENTGUARD_LOG_ENCRYPTION_KEY", None)

        with self.assertRaises(RuntimeError):
            encrypt_text("secret log")

    def test_prefix_like_plaintext_is_still_encrypted(self):
        os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")
        plaintext = f"{ENCRYPTED_VALUE_PREFIX}not-actually-ciphertext"

        encrypted = encrypt_text(plaintext)

        self.assertIsNotNone(encrypted)
        self.assertTrue(encrypted.startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertNotEqual(encrypted, plaintext)
        self.assertEqual(decrypt_text(encrypted), plaintext)

    def test_plaintext_legacy_values_read_without_key(self):
        os.environ.pop("AGENTGUARD_LOG_ENCRYPTION_KEY", None)

        self.assertEqual(decrypt_text("legacy plaintext"), "legacy plaintext")


if __name__ == "__main__":
    unittest.main()

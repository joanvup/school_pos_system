"""Contrato del registro de pasarelas: solo PayU (WP3).

La verificación de firma, montos e idempotencia está en test_payu.py.
"""
import unittest
from types import SimpleNamespace as NS

from app.db import base as _db_base  # noqa: F401  (registra los modelos)
from app.payment_providers.registry import get_active_provider, get_all_providers, get_provider


class FakeSession:
    def query(self, *_):
        return self

    def filter(self, *_):
        return self

    def first(self):
        return None


class RegistryContractTest(unittest.TestCase):
    def test_only_payu_is_registered(self):
        self.assertEqual(set(get_all_providers()), {"payu"})
        self.assertIsNone(get_provider("wompi"))
        self.assertIsNone(get_provider("mercadopago"))

    def test_payu_exposes_required_contract(self):
        provider = get_provider("payu")
        self.assertIsNotNone(provider)
        self.assertTrue(provider.name)
        self.assertTrue(callable(provider.get_methods))
        self.assertTrue(callable(provider.init_recharge))
        self.assertTrue(callable(provider.handle_notification))

    def test_payu_methods_include_pse(self):
        provider = get_provider("payu")
        self.assertIn("pse", [method.id for method in provider.get_methods()])

    def test_active_provider_falls_back_to_payu(self):
        provider = get_active_provider(FakeSession())
        self.assertEqual(provider.name, "payu")


if __name__ == "__main__":
    unittest.main()

"""Malformed images never need credentials or inference reservations."""
import pytest
from fastapi import HTTPException
from services.api.document_extraction import extract_document


def test_invalid_image_rejected_before_provider_reservation():
    class NoProviderStore:
        def reserve_calls(self, *_args):
            pytest.fail('Malformed input must not reserve inference')

    with pytest.raises(HTTPException) as error:
        extract_document(NoProviderStore(), 'isolated-test', b'not-an-image', 'bad.png', 'document_extraction')
    assert error.value.status_code == 422

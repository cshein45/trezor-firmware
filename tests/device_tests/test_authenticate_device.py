import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import extensions as ext

from trezorlib import device, models
from trezorlib.debuglink import SessionDebugWrapper as Session

from ..common import compact_size

pytestmark = pytest.mark.models("safe")

ROOT_PUBLIC_KEY = {
    models.T2B1: bytes.fromhex(
        "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
    ),
    models.T3T1: bytes.fromhex(
        "04e48b69cd7962068d3cca3bcc6b1747ef496c1e28b5529e34ad7295215ea161dbe8fb08ae0479568f9d2cb07630cb3e52f4af0692102da5873559e45e9fa72959"
    ),
    models.T3B1: bytes.fromhex(
        "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
    ),
    models.T3W1: bytes.fromhex(
        "04521192e173a9da4e3023f747d836563725372681eba3079c56ff11b2fc137ab189eb4155f371127651b5594f8c332fc1e9c0f3b80d4212822668b63189706578"
    ),
}


@pytest.mark.parametrize(
    "challenge",
    (
        b"",
        b"hello world",
        b"\x00" * 1024,
        bytes.fromhex(
            "21f3d40e63c304d0312f62eb824113efd72ba1ee02bef6777e7f8a7b6f67ba16"
        ),
    ),
)
def test_authenticate_device(session: Session, challenge: bytes) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    proof = device.authenticate(session, challenge)
    certs = [x509.load_der_x509_certificate(cert) for cert in proof.certificates]

    # Verify the last certificate in the certificate chain against trust anchor.
    root_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), ROOT_PUBLIC_KEY[session.model]
    )
    root_public_key.verify(
        certs[-1].signature,
        certs[-1].tbs_certificate_bytes,
        certs[-1].signature_algorithm_parameters,
    )

    # Verify the certificate chain.
    for cert, ca_cert in zip(certs, certs[1:]):
        assert cert.issuer == ca_cert.subject

        ca_basic_constraints = ca_cert.extensions.get_extension_for_class(
            ext.BasicConstraints
        ).value
        assert ca_basic_constraints.ca is True

        try:
            basic_constraints = cert.extensions.get_extension_for_class(
                ext.BasicConstraints
            ).value
            if basic_constraints.ca:
                assert basic_constraints.path_length < ca_basic_constraints.path_length
        except ext.ExtensionNotFound:
            pass

        ca_cert.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_algorithm_parameters,
        )

    # Verify that the common name matches the Trezor model.
    common_name = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0]
    assert common_name.value.startswith(session.model.internal_name)

    # Verify the signature of the challenge.
    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    certs[0].public_key().verify(proof.signature, data, ec.ECDSA(hashes.SHA256()))

from xovis.models.hub_auto import Device, DeviceId
from xovis.utils.privacy import AIPrivacySession


def test_privacy_forward_pass_sanitization():
    """
    Tier 1 - Stateless Unit Test: Test Forward Pass (Sanitization).
    Ensures BLOCK fields are removed and HASH fields are pseudonymized.
    """
    session = AIPrivacySession()
    device = Device(
        device_name="Xovis Kitchen",
        device_group="Office Xovis",
        customer="Acme Corp",
        id=DeviceId(root="00:1E:C0:A0:22:35"),
        ip="10.10.10.2",
        type="PC2S",
    )

    sanitized = session.sanitize(device)

    # BLOCK verification: ip must be entirely missing
    assert "ip" not in sanitized

    # HASH verification: device_name, device_group, customer, and id must be hashed
    assert sanitized["device_name"].startswith("Device_")
    assert sanitized["device_group"].startswith("Device_")
    assert sanitized["customer"].startswith("Customer_")
    assert sanitized["id"].startswith("Id_")

    # Plain verification: type should remain unchanged
    assert sanitized["type"] == "PC2S"


def test_privacy_reverse_pass_restoration():
    """
    Tier 1 - Stateless Unit Test: Test Reverse Pass (Restoration).
    Ensures hashes can be mapped back to their original plaintext values.
    """
    session = AIPrivacySession()
    real_mac = "00:1E:C0:A0:22:35"
    real_customer = "Acme Corp"

    device = Device(customer=real_customer, id=DeviceId(root=real_mac))

    sanitized = session.sanitize(device)

    # Create mock LLM arguments using the hashes
    llm_args = {
        "id": sanitized["id"],
        "customer": sanitized["customer"],
        "other_field": "unaffected",
    }

    restored = session.restore(llm_args)

    assert restored["id"] == real_mac
    assert restored["customer"] == real_customer
    assert restored["other_field"] == "unaffected"


def test_privacy_collection_handling():
    """
    Tier 1 - Stateless Unit Test: Test Collection Handling.
    Ensures deep traversal of nested lists and models.
    """
    session = AIPrivacySession()
    devices = [
        Device(id=DeviceId(root="00:1E:C0:A0:22:31"), customer="Cust1"),
        Device(id=DeviceId(root="00:1E:C0:A0:22:32"), customer="Cust2"),
    ]

    sanitized_list = session.sanitize(devices)

    assert len(sanitized_list) == 2
    assert sanitized_list[0]["id"].startswith("Id_")
    assert sanitized_list[1]["id"].startswith("Id_")
    assert sanitized_list[0]["id"] != sanitized_list[1]["id"]

    # Restore the whole list
    restored_list = session.restore(sanitized_list)
    assert restored_list[0]["id"] == "00:1E:C0:A0:22:31"
    assert restored_list[1]["id"] == "00:1E:C0:A0:22:32"
    assert restored_list[0]["customer"] == "Cust1"
    assert restored_list[1]["customer"] == "Cust2"


def test_privacy_session_salt_isolation():
    """
    Tier 1 - Stateless Unit Test: Test Salt Isolation.
    Ensures hashes are different across different sessions for the same value.
    """
    session1 = AIPrivacySession()
    session2 = AIPrivacySession()
    val = "00:1E:C0:A0:22:35"

    # Using internal _generate_hash for direct test
    hash1 = session1._generate_hash("Id", val)
    hash2 = session2._generate_hash("Id", val)

    assert hash1 != hash2
    assert hash1.startswith("Id_")
    assert hash2.startswith("Id_")

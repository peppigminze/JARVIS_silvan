import pytest

from app.tools.ssrf_guard import check_ssrf, is_private_ip


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254", "::1", "fc00::1", "fe80::1"],
)
def test_private_and_reserved_ips_are_blocked(ip):
    assert is_private_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_public_ips_are_not_blocked(ip):
    assert is_private_ip(ip) is False


def test_ipv4_mapped_ipv6_loopback_is_blocked():
    """::ffff:127.0.0.1 must not bypass the loopback check just because
    it isn't literally inside 127.0.0.0/8 as an IPv6 address."""
    assert is_private_ip("::ffff:127.0.0.1") is True


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",  # resolves to loopback via DNS
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/admin",
        "http://metadata.google.internal/",
    ],
)
def test_check_ssrf_blocks_dangerous_urls(url):
    assert check_ssrf(url) is not None


@pytest.mark.parametrize("url", ["https://example.com/", "http://8.8.8.8/"])
def test_check_ssrf_allows_public_urls(url):
    assert check_ssrf(url) is None


def test_check_ssrf_rejects_non_http_schemes():
    assert check_ssrf("file:///etc/passwd") is not None
    assert check_ssrf("ftp://example.com/") is not None


def test_check_ssrf_rejects_url_without_hostname():
    assert check_ssrf("http://") is not None

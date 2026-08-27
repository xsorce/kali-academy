#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "academy"))

from wifi import band_for, parse_fields, supported_modes

assert band_for("2412") == "2.4 GHz"
assert band_for("5180") == "5 GHz"
assert band_for("5955") == "6 GHz"
assert parse_fields("driver: rtl8xxxu\nfirmware-version: 1.2") == {
    "driver": "rtl8xxxu", "firmware-version": "1.2"
}
assert supported_modes("Supported interface modes:\n\t * managed\n\t * monitor\nBand 1:") == "managed, monitor"
print("Wi-Fi self-test passed.")

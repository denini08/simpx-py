import qrcode
import io
from PIL import Image

def print_qr_to_terminal(text: str):
    """
    Prints a QR code representing the given text to the terminal.

    Args:
        text: The string to encode in the QR code.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    qr.print_ascii()

if __name__ == '__main__':
    print_qr_to_terminal("https://www.example.com")

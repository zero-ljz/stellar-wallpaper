"""Use the macOS system CA bundle for HTTPS in the frozen application."""

import os

# The bundled OpenSSL may look for certificates in the build machine's Python installation.
os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

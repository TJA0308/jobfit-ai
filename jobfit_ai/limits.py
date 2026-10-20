"""Shared application limits; deployment request limits are still required."""
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARS = 20_000
MAX_RESUME_CHARS = 100_000
MAX_PDF_PAGES = 30
MAX_DOCX_XML_BYTES = 2 * 1024 * 1024

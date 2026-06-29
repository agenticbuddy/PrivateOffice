"""Editor-supported document formats.

`EXT_MIME` maps a file extension to its MIME type for the formats the editor can
open/edit. `CREATABLE` is the subset offered for "create new" (OOXML default per the
project decision). Upload validation accepts any extension in `EXT_MIME`.
"""

# Extension -> MIME for CO-editable formats (text / spreadsheet / presentation).
EXT_MIME: dict[str, str] = {
    # text documents
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "odt": "application/vnd.oasis.opendocument.text",
    "rtf": "application/rtf",
    "txt": "text/plain",
    # spreadsheets
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "csv": "text/csv",
    # presentations
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "odp": "application/vnd.oasis.opendocument.presentation",
}

# Categories help the UI group/icon files.
CATEGORY: dict[str, str] = {
    **{e: "document" for e in ("docx", "doc", "odt", "rtf", "txt")},
    **{e: "spreadsheet" for e in ("xlsx", "xls", "ods", "csv")},
    **{e: "presentation" for e in ("pptx", "ppt", "odp")},
}

# Offered for "create new" — OOXML default.
CREATABLE = ("docx", "xlsx", "pptx")


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_supported(name: str) -> bool:
    return ext_of(name) in EXT_MIME


def mime_for(name: str) -> str | None:
    return EXT_MIME.get(ext_of(name))


def category_for(name: str) -> str:
    return CATEGORY.get(ext_of(name), "document")

import os

import flet as ft

IMAGE_FILE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "bmp", "gif"]


def resolve_initial_directory(initial_path: str | None, fallback_directory: str | None = None) -> str | None:
    candidate = (initial_path or "").strip().strip('"')
    if candidate:
        if os.path.isfile(candidate):
            candidate = os.path.dirname(candidate)
        if os.path.isdir(candidate):
            return candidate

    fallback = (fallback_directory or "").strip().strip('"')
    if fallback and os.path.isdir(fallback):
        return fallback
    return None


def ensure_page_file_picker(page: ft.Page) -> ft.FilePicker:
    picker = getattr(page, "_temelmarket_file_picker", None)
    if isinstance(picker, ft.FilePicker):
        if picker not in page.services:
            page.services.append(picker)
            page.update()
        return picker

    picker = ft.FilePicker()
    page.services.append(picker)
    setattr(page, "_temelmarket_file_picker", picker)
    page.update()
    return picker


async def pick_directory_path(
    page: ft.Page,
    dialog_title: str,
    initial_path: str | None = None,
    fallback_directory: str | None = None,
) -> str | None:
    picker = ensure_page_file_picker(page)
    return await picker.get_directory_path(
        dialog_title=dialog_title,
        initial_directory=resolve_initial_directory(initial_path, fallback_directory),
    )


async def pick_single_file_path(
    page: ft.Page,
    dialog_title: str,
    *,
    initial_path: str | None = None,
    fallback_directory: str | None = None,
    file_type: ft.FilePickerFileType = ft.FilePickerFileType.ANY,
    allowed_extensions: list[str] | None = None,
) -> str | None:
    picker = ensure_page_file_picker(page)
    files = await picker.pick_files(
        dialog_title=dialog_title,
        initial_directory=resolve_initial_directory(initial_path, fallback_directory),
        file_type=file_type,
        allowed_extensions=allowed_extensions,
        allow_multiple=False,
    )
    if not files:
        return None
    return files[0].path or None


async def pick_image_file_path(
    page: ft.Page,
    dialog_title: str,
    initial_path: str | None = None,
    fallback_directory: str | None = None,
) -> str | None:
    return await pick_single_file_path(
        page,
        dialog_title,
        initial_path=initial_path,
        fallback_directory=fallback_directory,
        file_type=ft.FilePickerFileType.CUSTOM,
        allowed_extensions=IMAGE_FILE_EXTENSIONS,
    )

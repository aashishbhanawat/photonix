from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponseRedirect, JsonResponse)
from django.shortcuts import get_object_or_404

from photonix.photos.models import Library, PhotoFile
from photonix.photos.utils.thumbnails import get_thumbnail


def thumbnailer(request, type, id, width, height, crop, quality):
    width = int(width)
    height = int(height)
    quality = int(quality)

    thumbnail_size_index = None
    force_accurate = False
    for i, thumbnail_size in enumerate(settings.THUMBNAIL_SIZES):
        if width == thumbnail_size[0] and height == thumbnail_size[1] and crop == thumbnail_size[2] and quality == thumbnail_size[3]:
            thumbnail_size_index = i
            force_accurate = thumbnail_size[5]
            break

    if thumbnail_size_index is None:
        return HttpResponseNotFound('No photo thumbnail with these parameters')

    photo_id = None
    photo_file_id = None
    if type == 'photo':
        photo_id = id
    elif type == 'photofile':
        photo_file_id = id

    path = get_thumbnail(photo_file=photo_file_id, photo=photo_id, width=width, height=height,
                         crop=crop, quality=quality, return_type='url', force_accurate=force_accurate)
    return HttpResponseRedirect(path)


@login_required
def upload(request):
    if 'library_id' not in request.GET:
        return JsonResponse({'ok': False, 'message': 'library_id must be supplied as GET parameter'}, status=400)

    lib = get_object_or_404(Library, id=request.GET['library_id'], users__user=request.user)
    libpath = lib.paths.filter(type='St').first()
    if not libpath:
        return JsonResponse({'ok': False, 'message': 'Library has no storage path configured'}, status=400)

    storage_root = Path(libpath.path).resolve()
    for fn, file in request.FILES.items():
        # Sanitize filename to prevent path traversal. We use the key as the filename to match previous behavior.
        safe_filename = Path(fn).name
        if not safe_filename:
            safe_filename = Path(file.name).name

        dest = (storage_root / safe_filename).resolve()

        # Security check: ensure the destination is still within storage_root
        if not dest.is_relative_to(storage_root):
            return JsonResponse({'ok': False, 'message': f'Invalid filename: {fn}'}, status=400)

        with open(dest, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
    return JsonResponse({'ok': True})


def dummy_thumbnail_response(request, path):
    # Only used during testing to return thumbnail images. Everywhere else, Nginx handles these requests.
    filepath = str(Path(settings.THUMBNAIL_ROOT) / path)
    try:
        with open(filepath, 'rb') as f:
            return HttpResponse(f.read(), content_type='image/jpeg')
    except FileNotFoundError:
        # e.g. photofile/256x256_cover_q50/3bfc122c-cbb1-4f21-843a-db79f1d9229d.jpg
        parts = path.split('/')
        photo_file_id = parts[-1].split('.')[0]
        width, height, crop, quality = parts[-2].split('_')
        width, height = [int(x) for x in width.split('x')]
        quality = int(quality[1:])
        get_thumbnail(photo_file=photo_file_id, width=width,
                      height=height, crop=crop, quality=quality, return_type='path')
        with open(filepath, 'rb') as f:
            return HttpResponse(f.read(), content_type='image/jpeg')

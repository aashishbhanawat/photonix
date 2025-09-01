import os
from pathlib import Path

from django.conf import settings
from django.utils import timezone
import pytest

from .factories import LibraryFactory
from photonix.photos.models import PhotoFile, Task
from photonix.photos.utils.fs import download_file
from photonix.photos.utils.raw import generate_jpeg, identified_as_jpeg


PHOTOS = [
    # -e argument to dcraw means JPEG was extracted without any processing
    ('Adobe DNG Converter - Canon EOS 5D Mark III - Lossy JPEG compression (3_2).DNG',  'dcraw -e', 1236950, ['https://epixstudios.co.uk/uploads/filer_public/36/fa/36fad1f0-8032-45da-bad8-7d9b7d490d99/adobe_dng_converter_-_canon_eos_5d_mark_iii_-_lossy_jpeg_compression_3_2.dng', 'https://raw.pixls.us/getfile.php/1023/nice/Adobe%20DNG%20Converter%20-%20Canon%20EOS%205D%20Mark%20III%20-%20Lossy%20JPEG%20compression%20(3:2).DNG']),
    ('Apple - iPhone 8 - 16bit (4_3).dng',                                              'dcraw -w', 772618, ['https://epixstudios.co.uk/uploads/filer_public/5f/f3/5ff34f05-2c6a-4b5d-a1c5-b0d73f9273d9/apple_-_iphone_8_-_16bit_4_3.dng', 'https://raw.pixls.us/getfile.php/2835/nice/Apple%20-%20iPhone%208%20-%2016bit%20(4:3).dng']),  # No embedded JPEG
    ('Canon - Canon PowerShot SX20 IS.DNG',                                             'dcraw -w', 1828344, ['https://epixstudios.co.uk/uploads/filer_public/4e/28/4e28cab6-0523-48e3-a70b-e5bdaf041bb1/canon_-_canon_powershot_sx20_is.dng', 'https://raw.pixls.us/getfile.php/861/nice/Canon%20-%20Canon%20PowerShot%20SX20%20IS.DNG']),  # Embedded image but low resolution and not a JPEG
    ('Canon - EOS 7D - sRAW2 (sRAW) (3:2).CR2',                                         'dcraw -e', 2264602, ['https://epixstudios.co.uk/uploads/filer_public/7f/a2/7fa2e9d6-a1fc-4ca6-bb19-306c1320c9c4/canon_-_eos_7d_-_sraw2_sraw_32.cr2', 'https://raw.pixls.us/getfile.php/129/nice/Canon%20-%20EOS%207D%20-%20sRAW2%20(sRAW)%20(3:2).CR2']),
    ('Canon - Powershot SX110IS - CHDK.CR2',                                            'dcraw -w', 1493825, ['https://epixstudios.co.uk/uploads/filer_public/ab/6b/ab6b7ff2-f892-4698-add4-3c304142cfa6/canon_-_powershot_sx110is_-_chdk.cr2', 'https://raw.pixls.us/getfile.php/144/nice/Canon%20-%20Powershot%20SX110IS%20-%20CHDK.CR2']),  # No embedded JPEG, No metadata about image dimensions for us to compare against
    ('Leica - D-LUX 5 - 16_9.RWL',                                                      'dcraw -w', 1478207, ['https://epixstudios.co.uk/uploads/filer_public/a5/0f/a50f6ddb-ab72-4e78-8e68-f6131e3a7dcd/leica_-_d-lux_5_-_16_9.rwl', 'https://raw.pixls.us/getfile.php/2808/nice/Leica%20-%20D-LUX%205%20-%2016:9.RWL']),  # Less common aspect ratio, fairly large embedded JPEG but not similar enough to the raw's dimensions
    ('Nikon - 1 J1 - 12bit compressed (Lossy (type 2)) (3_2).NEF',                      'dcraw -e', 635217, ['https://epixstudios.co.uk/uploads/filer_public/a6/7c/a67c538f-254d-4793-862c-4b3dc3bda0ef/nikon_-_1_j1_-_12bit_compressed_lossy_type_2_3_2.nef', 'https://raw.pixls.us/getfile.php/2956/nice/Nikon%20-%201%20J1%20-%2012bit%20compressed%20(Lossy%20(type%202))%20(3:2).NEF']),
    ('Sony - SLT-A77 - 12bit compressed (3_2).ARW',                                     'dcraw -w', 859814, ['https://epixstudios.co.uk/uploads/filer_public/42/a6/42a6b056-7e33-4100-b652-5b96aff8bc22/sony_-_slt-a77_-_12bit_compressed_3_2.arw', 'https://raw.pixls.us/getfile.php/2691/nice/Sony%20-%20SLT-A77%20-%2012bit%20compressed%20(3:2).ARW']),  # Large embedded JPEG but not the right aspect ratio and smaller than raw
]


def test_extract_jpg():
    for fn, intended_process_params, intended_filesize, urls in PHOTOS:
        raw_photo_path = str(Path(__file__).parent / 'photos' / fn)
        if not os.path.exists(raw_photo_path):
            for url in urls:
                try:
                    download_file(url, raw_photo_path)
                    if not os.path.exists(raw_photo_path) or os.stat(raw_photo_path).st_size < 1024 * 1024:
                        try:
                            os.remove(raw_photo_path)
                        except:
                            pass
                    else:
                        break
                except:
                    pass

        output_path, _, process_params, _ = generate_jpeg(raw_photo_path)

        assert process_params == intended_process_params
        assert identified_as_jpeg(output_path) == True
        filesizes = [intended_filesize, os.stat(output_path).st_size]
        assert min(filesizes) / max(filesizes) > 0.8  # Within 20% of the intended JPEG filesize

        os.remove(output_path)



"""Print orientation from invented color swatches, without changing source bytes."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from web.report_pdf import _photo_image


class ReportPhotoTests(unittest.TestCase):
    def test_rotated_and_mirrored_photographs_match_display_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            cases=[(1,((100,378),(572,378))), (2,((572,378),(100,378))),
                   (6,((336,100),(336,650))), (8,((336,650),(336,100)))]
            for orientation,(red_at,blue_at) in cases:
                with self.subTest(orientation=orientation):
                    path=Path(directory)/(str(orientation)+'.jpg')
                    source=Image.new('RGB',(100,80),(235,15,25));source.paste((15,25,235),(50,0,100,80))
                    exif=source.getexif();exif[274]=orientation;source.save(path,exif=exif)
                    raw=path.read_bytes();mtime=path.stat().st_mtime_ns
                    printed=Image.open(_photo_image({'_local_path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}))
                    red=printed.getpixel(red_at);blue=printed.getpixel(blue_at)
                    self.assertGreater(red[0],200);self.assertLess(red[2],50)
                    self.assertGreater(blue[2],200);self.assertLess(blue[0],50)
                    self.assertEqual(printed.size,(672,756));self.assertNotIn(274,printed.getexif())
                    self.assertEqual(path.read_bytes(),raw);self.assertEqual(path.stat().st_mtime_ns,mtime)

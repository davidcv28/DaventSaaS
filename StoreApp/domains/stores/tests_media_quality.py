"""
Tests de media_quality (aviso de resolución/proporción por slot) y del
nuevo tope de producto en normalize_image. Nunca se rechaza por calidad:
inspect/quality solo informan.
"""
import io

from django.test import SimpleTestCase
from PIL import Image

from StoreApp.domains.stores.services.imaging import MAX_SIDE_PRODUCT, normalize_image
from StoreApp.domains.stores.services.media_quality import KIND_TO_SLOT, SLOT_SPECS, inspect, quality


def _upload(size, mode = 'RGB', color = (200, 30, 30), fmt = 'PNG', exif = None):
    buffer      =   io.BytesIO()
    Image.new(mode, size, color).save(buffer, format = fmt, exif = exif)
    buffer.seek(0)
    return buffer


def _exif(orientation):
    exif        =   Image.Exif()
    exif[0x0112]=   orientation
    return exif.tobytes()


class MediaQualityInspectTests(SimpleTestCase):
    """inspect(): dimensiones EXIF-corregidas + flag soft por slot."""

    def test_small_image_is_soft_in_every_slot(self):
        for slot in SLOT_SPECS:
            with self.subTest(slot = slot):
                info    =   inspect(_upload((400, 400)), slot)
                self.assertEqual((info['width'], info['height']), (400, 400))
                self.assertTrue(info['soft'])
                self.assertTrue(info['min_side'] > 400)

    def test_large_image_is_not_soft_in_any_slot(self):
        for slot in SLOT_SPECS:
            with self.subTest(slot = slot):
                info    =   inspect(_upload((3000, 3000)), slot)
                self.assertFalse(info['soft'])
                self.assertTrue(info['ratio_ok'])

    def test_pano_cover_keeps_less_useful_side(self):
        # 5000x1000 (5:1): para la portada apaisada el lado útil tras el
        # recorte 16:9 es ~1778 < 2200 -> soft; en galería cuadrada min=1000.
        info    =   inspect(_upload((5000, 1000)), 'cover')
        self.assertTrue(info['soft'])
        self.assertLess(info['usable'], 2200)

    def test_exif_orientation_swaps_reported_size(self):
        # JPEG 100x400 con EXIF orientation=6 se muestra 400x100.
        info    =   inspect(_upload((100, 400), fmt = 'JPEG', exif = _exif(6)), 'logo')
        self.assertEqual((info['width'], info['height']), (400, 100))
        self.assertAlmostEqual(info['ratio'], 4.0, places = 2)

    def test_ratio_out_of_slot_range_flags_crop_hint(self):
        portrait    =   inspect(_upload((800, 1200)), 'cover')
        self.assertFalse(portrait['ratio_ok'])
        landscape   =   inspect(_upload((2400, 1200)), 'cover')   # ratio 2.0 -> ok
        self.assertTrue(landscape['ratio_ok'])

    def test_invalid_file_raises_value_error(self):
        import io as _io
        with self.assertRaises(ValueError):
            inspect(_io.BytesIO(b'no soy una imagen'), 'logo')


class MediaQualityPayloadTests(SimpleTestCase):
    """quality(): forma {ok, soft, hint} para la respuesta del upload."""

    def test_payload_shape_and_soft_warning(self):
        result  =   quality(_upload((400, 400)), 'logo')
        self.assertEqual(set(result), {'ok', 'soft', 'hint'})
        self.assertTrue(result['soft'])
        self.assertFalse(result['ok'])
        self.assertIn('800', result['hint'])

    def test_good_image_returns_ok_with_empty_hint(self):
        result  =   quality(_upload((1600, 1600)), 'gallery')
        self.assertTrue(result['ok'])
        self.assertFalse(result['soft'])
        self.assertEqual(result['hint'], '')

    def test_ratio_warning_alone_keeps_soft_false(self):
        # 900x300 (3:1) en producto: min=300 <1200 -> soft también; usar
        # una imagen grande pero alargada para aislar el aviso de recorte.
        result  =   quality(_upload((4000, 1500)), 'product')
        self.assertFalse(result['soft'])          # usable = min(4000,1500)=1500 >= 1200
        self.assertFalse(result['ok'])            # ratio 2.67 fuera de (0.75, 1.5)
        self.assertIn('cuadrado', result['hint'])

    def test_kind_without_slot_is_neutral(self):
        result  =   quality(_upload((100, 100)), 'chat')
        self.assertEqual(result, {'ok': True, 'soft': False, 'hint': ''})
        self.assertNotIn('chat', KIND_TO_SLOT)


class ProductMaxSideTests(SimpleTestCase):
    """MAX_SIDE_PRODUCT subió a 1600 (retina + ficha)."""

    def test_product_caps_at_1600_and_still_webp(self):
        body, ext, content_type =   normalize_image(_upload((3000, 3000)), 'product')
        self.assertEqual((ext, content_type), ('webp', 'image/webp'))
        width, height           =   Image.open(io.BytesIO(body)).size
        self.assertEqual(max(width, height), MAX_SIDE_PRODUCT)
        self.assertEqual(MAX_SIDE_PRODUCT, 1600)

    def test_exif_rotated_png_comes_out_upright_webp(self):
        # PNG 100x400 con EXIF orientation=6: el WebP sale 400x100 (derecho).
        body, ext, _            =   normalize_image(
            _upload((100, 400), fmt = 'PNG', exif = _exif(6)), 'product')
        self.assertEqual(ext, 'webp')
        out                     =   Image.open(io.BytesIO(body))
        self.assertEqual(out.format, 'WEBP')
        self.assertGreater(out.size[0], out.size[1])

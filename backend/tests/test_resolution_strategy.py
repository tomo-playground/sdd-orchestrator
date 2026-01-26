import unittest

from PIL import Image, ImageOps


class TestResolutionStrategy(unittest.TestCase):
    def test_image_ops_fit_top_centering(self):
        """Test if ImageOps.fit with centering=(0.5, 0.0) crops from the top."""
        # Create a 100x200 image with a red top half and blue bottom half
        img = Image.new("RGB", (100, 200), "blue")
        top_half = Image.new("RGB", (100, 100), "red")
        img.paste(top_half, (0, 0))

        # Crop to 100x100 square
        # centering=(0.5, 0.0) should keep the top (red) part
        cropped = ImageOps.fit(img, (100, 100), centering=(0.5, 0.0))

        # Check center pixel color (should be red)
        center_pixel = cropped.getpixel((50, 50))
        self.assertEqual(center_pixel, (255, 0, 0), f"Expected red pixel from top half, got {center_pixel}")

    def test_image_ops_fit_default_centering(self):
        """Test default centering (0.5, 0.5) behavior for comparison."""
        img = Image.new("RGB", (100, 300), "blue")
        # Top: Red, Middle: Green, Bottom: Blue
        draw = Image.new("RGB", (100, 100), "red")
        img.paste(draw, (0, 0))
        draw = Image.new("RGB", (100, 100), "green")
        img.paste(draw, (0, 100))

        # Crop to 100x100 square with default centering (middle)
        cropped = ImageOps.fit(img, (100, 100), centering=(0.5, 0.5))

        # Check center pixel color (should be green)
        center_pixel = cropped.getpixel((50, 50))
        self.assertEqual(center_pixel, (0, 128, 0), f"Expected green pixel from middle, got {center_pixel}")

if __name__ == "__main__":
    unittest.main()

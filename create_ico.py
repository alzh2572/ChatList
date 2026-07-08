"""Генерация app.ico — зелёный круг на чёрном фоне."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
OUTPUT = Path(__file__).parent / "app.ico"
BACKGROUND = (0, 0, 0, 255)
CIRCLE_COLOR = (0, 200, 0, 255)


def create_icon_image(size: tuple[int, int]) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, BACKGROUND)
    draw = ImageDraw.Draw(img)
    margin = max(1, min(width, height) // 16)
    draw.ellipse(
        (margin, margin, width - margin - 1, height - margin - 1),
        fill=CIRCLE_COLOR,
    )
    return img


def main() -> None:
    images = [create_icon_image(size) for size in SIZES]
    images[0].save(
        OUTPUT,
        format="ICO",
        sizes=SIZES,
        append_images=images[1:],
    )
    print(f"Создан: {OUTPUT}")


if __name__ == "__main__":
    main()

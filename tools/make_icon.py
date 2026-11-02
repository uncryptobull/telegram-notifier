from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "telegram_notifier" / "assets"
root.mkdir(exist_ok=True)
image = Image.new("RGBA", (256, 256))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=44, fill="#327fb2")
draw.ellipse((104, 178, 152, 218), fill="white")
draw.rounded_rectangle((76, 60, 180, 180), radius=48, fill="white")
draw.rectangle((76, 116, 180, 180), fill="white")
draw.polygon([(76, 159), (56, 187), (200, 187), (180, 159)], fill="white")
draw.ellipse((117, 42, 139, 66), fill="white")
image.save(root / "app.png")
image.save(root / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

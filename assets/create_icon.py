"""Run once to generate assets/icon.png"""
from PIL import Image, ImageDraw

SIZE = 64
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background circle
draw.ellipse([2, 2, SIZE - 2, SIZE - 2], fill=(45, 45, 80, 220))

# Microphone body
draw.rounded_rectangle([22, 10, 42, 36], radius=10, fill=(255, 255, 255, 240))

# Microphone stand arc
draw.arc([14, 24, 50, 50], start=0, end=180, fill=(255, 255, 255, 240), width=3)

# Stand line
draw.line([32, 49, 32, 56], fill=(255, 255, 255, 240), width=3)

# Base
draw.line([24, 56, 40, 56], fill=(255, 255, 255, 240), width=3)

img.save("icon.png")
print("icon.png created")

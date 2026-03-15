from PIL import Image, ImageDraw
import os

def generate_icon(size, color, output_path):
    """Generates a simple circular icon with a shield."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw a blue circle
    draw.ellipse([(0, 0), (size - 1, size - 1)], fill=color)

    # Simple shield shape
    shield_poly = [
        (size * 0.5, size * 0.2),
        (size * 0.2, size * 0.3),
        (size * 0.2, size * 0.6),
        (size * 0.5, size * 0.8),
        (size * 0.8, size * 0.6),
        (size * 0.8, size * 0.3),
    ]
    draw.polygon(shield_poly, fill="white")

    image.save(output_path)

if __name__ == "__main__":
    icons_dir = "extension/icons"
    os.makedirs(icons_dir, exist_ok=True)

    sizes = [16, 48, 128]
    blue_color = "#007BFF"

    for size in sizes:
        output_path = os.path.join(icons_dir, f"icon{size}.png")
        generate_icon(size, blue_color, output_path)
        print(f"Generated {output_path}")

    # Clean up old svg files
    for file_name in os.listdir(icons_dir):
        if file_name.endswith(".svg"):
            os.remove(os.path.join(icons_dir, file_name))
            print(f"Removed {file_name}")

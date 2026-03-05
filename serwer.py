import io
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import Response, JSONResponse
from PIL import Image, ImageDraw, ImageChops, ImageFont


app = FastAPI()

def min_max(file_path: str):
    try:
        result = subprocess.run(["gdalinfo", "-json", "-stats", file_path], capture_output=True, text=True)
        band_data = json.loads(result.stdout)["bands"][0]
        minimum = band_data.get("minimum")
        maximum = band_data.get("maximum")
        return float(minimum or 0), float(maximum or 3000)
    except:
        return 0.0, 3000.0

def color_file(file_path: str, minimum: float, maximum: float):
    step = (maximum - minimum) / 4
    colors = [
        "nv 0 0 0 0",
        f"{minimum:.1f} 50 160 50",
        f"{minimum+step:.1f} 255 255 0",
        f"{minimum+step*2:.1f} 255 165 0",
        f"{minimum+step*3:.1f} 165 42 42",
        f"{maximum:.1f} 255 255 255"
    ]
    Path(file_path).write_text("\n".join(colors), encoding="utf-8")

def legend(minimum: float, maximum: float, height_px: int) -> Image.Image:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import colors, cm

    color_stops = [
        (50/255, 160/255, 50/255),
        (255/255, 255/255, 0/255),
        (255/255, 165/255, 0/255),
        (165/255, 42/255, 42/255),
        (255/255, 255/255, 255/255),
    ]
    colormap = colors.LinearSegmentedColormap.from_list("dem", color_stops, N=256)

    normalizer = colors.Normalize(vmin=minimum, vmax=maximum)
    scale_colors = cm.ScalarMappable(norm=normalizer, cmap=colormap)
    scale_colors.set_array([])

    figure, axis = plt.subplots(figsize=(1.0, 4.0))
    figure.subplots_adjust(left=0.3, right=0.7, top=0.9, bottom=0.1) # marginesy legenda
    colorbar = figure.colorbar(scale_colors, cax=axis)
    colorbar.set_label("m n.p.m.")

    colorbar.ax.text(0.5, -0.08, f"Min: {int(minimum)} m",
                 ha="center", va="top", fontsize=8, transform=colorbar.ax.transAxes)
    colorbar.ax.text(0.5, -0.18, f"Max: {int(maximum)} m",
                 ha="center", va="top", fontsize=8, transform=colorbar.ax.transAxes)

    virtual_file_legend = io.BytesIO()
    figure.savefig(virtual_file_legend, format="png", dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    virtual_file_legend.seek(0) #poczatek
    legend_image = Image.open(virtual_file_legend).convert("RGBA")

    scale = (height_px * 0.8) / legend_image.height
    new_size = (int(legend_image.width * scale), int(legend_image.height * scale))
    return legend_image.resize(new_size, Image.LANCZOS)


def add_title(image: Image.Image, title: str) -> Image.Image:
    font_size = max(10, int(image.height * 0.05))
    
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    max_title_width = image.width - 40
    avg_title_width = font_size * 0.6
    chars_per_line = int(max_title_width / avg_title_width)
    
    wrapped_lines = textwrap.wrap(title, width=chars_per_line)
    if not wrapped_lines:
        wrapped_lines = [title] # nazwa oryginalnego pliku
    
    line_height = font_size + 5
    title_bar_height = len(wrapped_lines) * line_height + 20
    
    new_height = image.height + title_bar_height 
    new_image = Image.new("RGB", (image.width, new_height), "white")
    draw = ImageDraw.Draw(new_image)
    
    y_position = 10 
    for line in wrapped_lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        x_position = (image.width - text_width) // 2
        draw.text((x_position, y_position), line, fill="black", font=font)
        y_position += line_height
    
    new_image.paste(image, (0, title_bar_height))
    return new_image


def add_legend(image: Image.Image, minimum: float, maximum: float):
    width, height = image.size
    legend_image = legend(minimum, maximum, height)
    legend_width, legend_height = legend_image.size

    margin = 10
    new_width = width + legend_width + 2 * margin 
    final_image = Image.new("RGB", (new_width, height), "white")
    final_image.paste(image, (0, 0))

    x_position = width + margin
    y_position = (height - legend_height) // 2
    final_image.paste(legend_image, (x_position, y_position), legend_image)
    return final_image

@app.post("/process")
async def process(
    file: UploadFile = File(...), 
    title: str = Form(None),
    output_format: str = Form("png")
):
    temp_dir = tempfile.mkdtemp()
    try:
        input_path = os.path.join(temp_dir, "input.tif")
        with open(input_path, "wb") as f:
            f.write(await file.read())

        minimum, maximum = min_max(input_path)
        colors = os.path.join(temp_dir, "colors.txt")
        color_file(colors, minimum, maximum)
        
        color_tif = os.path.join(temp_dir, "color.tif")
        hillshade_tif = os.path.join(temp_dir, "hillshade.tif")
        
        try:
            subprocess.run(["gdaldem", "color-relief", "-alpha", input_path, colors, color_tif], check=True)
            subprocess.run(["gdaldem", "hillshade", "-z", "1.5", input_path, hillshade_tif], check=True)
        except FileNotFoundError:
            return JSONResponse({"error": "Nie znaleziono polecenia gdaldem"}, status_code=500)
        except subprocess.CalledProcessError as e:
            return JSONResponse({"error": f"Błąd gdaldem: kod {e.returncode}"}, status_code=500)

        color_image = Image.open(color_tif).convert("RGBA")
        hillshade_image = Image.open(hillshade_tif).convert("RGBA").resize(color_image.size)
        combined_map = ImageChops.multiply(color_image, hillshade_image)

        final_image = add_legend(combined_map, minimum, maximum)

        if title:
            final_image = add_title(final_image, title)

        valid_format = output_format.lower().strip()
        if valid_format not in ("png", "jpg", "jpeg"):
            valid_format = "png"  # domyslnie png
        
        normalized_format = "jpg" if valid_format in ("jpg", "jpeg") else "png"
        
        pil_format = "JPEG" if normalized_format == "jpg" else "PNG"
        media_type = "image/jpeg" if normalized_format == "jpg" else "image/png"
        
        output_buffer = io.BytesIO()
        if pil_format == "JPEG":
            final_image = final_image.convert("RGB")
            final_image.save(output_buffer, format=pil_format, quality=95)
        else:
            final_image.save(output_buffer, format=pil_format)
        
        return Response(output_buffer.getvalue(), media_type=media_type)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
import os
import queue
import re

import ffmpeg
import matplotlib.pyplot as plt
from PIL import Image

plt.rc("text", usetex=True)
plt.rc(
    "text.latex",
    preamble=r"\usepackage{amsmath} \usepackage{amsfonts} \usepackage{amssymb} \usepackage{xcolor}",
)

pattern = r"\$(.+?)\$"


def convert_srt_to_ass(input_srt_path, output_ass_path):
    """
    Scan the .srt file for any LaTeX, temporarily replace LaTeX with placeholder, then convert to a temporary .ass file. Then, insert the LaTeX back into the output .ass file.
    """
    latex = queue.Queue()
    with open(input_srt_path, "r", encoding="utf-8") as file:
        content = file.read()

    def replace_expression(match):
        original = match.group(0)
        latex.put(original)
        return "$temp$"

    modified_file = re.sub(pattern, replace_expression, content)
    with open("Temp.srt", "w", encoding="utf-8") as file:
        file.write(modified_file)

    ffmpeg.input("Temp.srt").output("Temp.ass", format="ass").run(overwrite_output=True)
    with (
        open("Temp.ass", "r", encoding="utf-8") as source_file,
        open("Temp2.ass", "w", encoding="utf-8") as destination_file,
    ):
        destination_file.write(source_file.read())

    with open("Temp2.ass", "r", encoding="utf-8") as file:
        content = file.read()

    def replace_expression(match):
        return latex.get()

    modified_file = re.sub(pattern, replace_expression, content)
    if not os.path.exists("./media"):
        os.makedirs("./media")
    with open(output_ass_path, "w", encoding="utf-8") as file:
        file.write(modified_file)

    os.remove("Temp.srt")
    os.remove("Temp.ass")
    os.remove("Temp2.ass")


def process_latex_from_ass(input_ass, output_ass_path):
    """
    Parse the LaTeX from the input .ass file, create transparent images for each LaTeX expression, and insert the images into the output .ass file.
    """
    with open(input_ass, "r", encoding="utf-8") as file:
        content = file.read()

    match_counter = 0

    def replace_expression(match):
        original = match.group(0)
        raw_latex = original[1:-1]
        nonlocal match_counter
        match_counter += 1
        return generate_image_ass(raw_latex, match_counter)

    modified_file = re.sub(pattern, replace_expression, content)

    with open(output_ass_path, "w", encoding="utf-8") as file:
        file.write(modified_file)


def generate_image_ass(raw_latex, match_counter):
    png_path = "./media/" + str(match_counter) + ".png"
    print(png_path, raw_latex)
    latex_to_transparent_image(raw_latex, png_path)
    with Image.open(png_path) as img:
        width, height = img.size
    bounding_box_width = round(width / 5, 2)
    bounding_box_height = round(height / 3.75, 2)
    downshift = min(round(bounding_box_height / 4, 2), 10)
    bounding_box = f"m 0 {str(downshift)} l {str(bounding_box_width)} {str(downshift)} {str(bounding_box_width)} {str(bounding_box_height + downshift)} 0 {str(bounding_box_height + downshift)} 0 {str(downshift)}"
    return (
        r"{\1a&HFF&\3a&HFF&\1img(" + png_path + ",0,0)\p1}" + bounding_box + r"{\p0\r}"
    )


def latex_to_transparent_image(latex_code, output_path):
    fig, ax = plt.subplots()
    ax.axis("off")

    text = ax.text(
        0, 0, f"${latex_code}$", fontsize=14, color="white", va="bottom", ha="left"
    )

    plt.draw()

    bbox = text.get_window_extent()

    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.set_size_inches(bbox_inches.width, bbox_inches.height)

    plt.savefig(
        output_path, bbox_inches="tight", pad_inches=0.05, transparent=True, dpi=300
    )
    plt.close()


# replace path

# replace file names as appropriate
convert_srt_to_ass("./media/videos/main/1080p60/Video.srt", "./media/temp.ass")
process_latex_from_ass("./media/temp.ass", "./media/Video.ass")
os.remove("./media/temp.ass")

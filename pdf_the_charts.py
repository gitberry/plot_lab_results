# usage poetry run python3 pdf_the_charts.py
# takes ALL IMAGES in the current folder into a PDF 
#   by putting the smaller ones together into letter sized pages, larger ones into Letter, Legal and Tabloid sized pages.
# output pdf named (current foldername).pdf 
# you are usually inside an output folder and the py is one below your virtual environment so this may be more like what you need:
# poetry run python3 ../../pdf_the_charts.py

import os
from PIL import Image

# GET FOLDER NAME FOR FILENAME
current_folder = os.path.basename(os.getcwd())
output_filename = f"{current_folder}.pdf"

# 300 DPI Target Dimensions (Width, Height)
LETTER = (2550, 3300)
LEGAL  = (2550, 4200)
LEDGER = (3300, 5100)

images = sorted([f for f in os.listdir('.') if f.lower().endswith('.png')])
small_charts = []
big_charts = []

for img_name in images:
    with Image.open(img_name) as img:
        img_copy = img.copy()
        if img.height == 553:
            small_charts.append(img_copy)
        elif img.height > 600:
            # SNAP TO TRAY
            if img.height <= 4200:
                canvas = Image.new('RGB', LEGAL, 'white')
            else:
                canvas = Image.new('RGB', LEDGER, 'white')
                if img.height > 5100 or img.width > 3300:
                    img_copy.thumbnail(LEDGER, Image.Resampling.LANCZOS)
            
            # TOP ALIGN: X is centered, Y is 0 (or a small margin like 50)
            x_offset = (canvas.width - img_copy.width) // 2
            canvas.paste(img_copy, (x_offset, 50)) # 50px top margin for breathing room
            big_charts.append(canvas)

# PROCESS SMALLS (Top Aligned on Letter)
final_pages = []
small_charts_per_page = 5
for i in range(0, len(small_charts), small_charts_per_page):
    chunk = small_charts[i:i+small_charts_per_page]
    page = Image.new('RGB', LETTER, 'white')
    
    y_ptr = 50 # Starting top margin
    for c in chunk:
        x_offset = (LETTER[0] - c.width) // 2
        page.paste(c, (x_offset, y_ptr))
        y_ptr += 573 # 553px + 20px gap
    final_pages.append(page)

final_pages.extend(big_charts)

if final_pages:
    final_pages[0].save(
        output_filename,
        save_all=True,
        append_images=final_pages[1:],
        resolution=300.0
    )
    print(f"Success! Created '{output_filename}' with all charts snapped to the top.")

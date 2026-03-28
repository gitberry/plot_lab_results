import sys
import json
import pandas as pd
import shutil
import secrets
import matplotlib.pyplot as plt
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# --- 1. THE SCHEMA ---
class LabResult(BaseModel):
    grouping: str
    when_date: datetime
    value: float
    test_name: str
    test_range_info: str = ""
    is_in_range: bool = True  # Default to True if missing
    attachment_cnt: int = 0
    attachment_url: str = ""
    test_note: str = ""
    model_config = ConfigDict(extra='ignore')

class RefEntry(BaseModel):
    data_test_name         : str
    functional_equivalent  : str
    test_name              : str
    safe_filename          : str
    test_abbreviation      : str
    common_clinical_uses   : str
    typical_reference_range: str

def format_title(title_string, abbrev_string):
    # If the abbreviation is already there, just return the title
    if abbrev_string.lower() in title_string.lower():
        return f"{title_string}"
    return f"{title_string} ({abbrev_string})"

def get_range_limits(range_str):
    #  Turns '150-500' into (150.0, 500.0)
    try:
        if not range_str or "-" not in str(range_str):
            return None, None
        parts = str(range_str).split('-')
        return float(parts[0]), float(parts[1])
    except:
        return None, None    

def parse_date(value, fallback):
    # purposely fails if data is formatted wonky - expects something like this: "May 12, 2017 12:13 PM"
    raw = value or fallback
    if not raw:
        return None       
    try:
        return datetime.strptime(raw, "%b %d, %Y %I:%M %p")
    except (ValueError, TypeError):
        return raw

def get_font(size):
    # KIS - same font for everything - just different sizes/colors
    # Common paths for Arial on different systems
    font_names = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    
    for name in font_names:
        try:
            # This works if the font is in your script folder or system path
            return ImageFont.truetype(name, size)
        except IOError:
            continue
            
    # If all else fails, return the tiny default font
    print("⚠️ Could not find system fonts, using default.")
    return ImageFont.load_default()

def add_branding_to_png(png_path, header_text, footer_text):
    # Open the image (ie graphicplot Matplotlib just made)
    img = Image.open(png_path)
    width, height = img.size
    
    # Define the height of your "strips" (e.g., 60 pixels)
    strip_height = 80
    
    # Create a new blank canvas that is taller than the original
    new_height = height + (strip_height * 2)
    # Using 'white' to match the plot background
    final_img = Image.new("RGB", (width, new_height), "white")
    
    # Paste the original plot in the middle
    final_img.paste(img, (0, strip_height))
    
    # Draw the text onto the new strips
    draw = ImageDraw.Draw(final_img)
    header_size = 36
    footer_size = 18
    
    # Load the fonts
    header_font = get_font(header_size)
    footer_font = get_font(footer_size)
    
    # Draw Header (Using header_font)
    draw.text((width/2, strip_height/2), header_text, 
              fill="black", font=header_font, anchor="mm")
    
    # Draw Footer (Using footer_font)
    draw.text((width/2, new_height - strip_height/2), footer_text, 
              fill="gray", font=footer_font, anchor="mm")
        
    # Overwrite the file with the "Sandwich" version
    final_img.save(png_path)
    print(f"Plot Header[{header_text}] Footer[{footer_text}] added.") 

def generate_health_plot(input_file, output_file): # , header_info = "", footer_info = ""):
    # Reads a TSV and generates basic plot    
    # Read and Process Data
    try:
        df = pd.read_csv(input_file, sep="\t")
        if df.empty:
            print(f"⚠️  Skipping plot: {input_file} is empty.")
            return            
        df['when_date'] = pd.to_datetime(df['when_date'])
        df = df.sort_values('when_date')
    except Exception as e:
        print(f"❌ Error processing data for {input_file}: {e}")
        return

    plt.style.use('seaborn-v0_8-whitegrid')

    # Determine Subplots
    unique_codes = df['test_name'].unique()
    num_plots = len(unique_codes)
    top_margin = 0.92 if num_plots < 5 else 0.88
    bottom_margin = 0.12 if num_plots > 1 else 0.10
    title_y = top_margin + 0.04
    foot_y = bottom_margin - 0.06

    # Create figure
    fig, axes = plt.subplots(nrows=num_plots, ncols=1, 
                             figsize=(14, 4 * num_plots), 
                             sharex=True)

    # Ensure axes is always a list even for 1 plot
    if num_plots == 1:
        axes = [axes]

    # Plotting Loop - for each unique (sub) test in the data for this "test" (ie it's a panel aka group)
    for i, code in enumerate(unique_codes):
        ax = axes[i]
        subset = df[df['test_name'] == code]
        note_color = '#444444'  #default dot color when all is OK (ie in range)

        # out of range logic and actions if needed
        distinct_values = subset['value'].dropna().unique()
        distinct_in_range = subset['is_in_range'].dropna().unique()
        if len(distinct_values) == 0 and len(distinct_in_range) > 0:            
            print("Found a Pass/Fail test with no numerical values!")
            subset['plot_val'] = subset['is_in_range'].map({True: 0, False: 1})
            # OK in green
            ok_data = subset[subset['plot_val'] == 0]
            ax.scatter(ok_data['when_date'], ok_data['plot_val'], color='green', s=100, label='OK')        
            # Plot the Outlier points (1) in Red
            out_data = subset[subset['plot_val'] == 1]
            ax.scatter(out_data['when_date'], out_data['plot_val'], color='red', s=100, label='OUTLIER')
            # Format the Y-Axis to show words instead of 0 and 1
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['OK', 'OUTLIER'])

        # Plot the data
        ax.plot(subset['when_date'], subset['value'], marker='o', 
                linestyle='-', color='#1f77b4')
                                
        # Logic for the "Note" field
        distinct_notes = subset['test_note'].dropna().unique()
        processed_notes = [str(n).replace('\\n', '\n') for n in distinct_notes]
        ranges = subset['test_range_info'].dropna().unique().tolist()
        distinct_range = f"Range info:\n{' | '.join(str(r) for r in ranges)}" if ranges else ""

        note_text = "Ref Info:\n" + "\n---\n".join(processed_notes) if processed_notes else distinct_range

        # Logic to make red dots for out of range data
        low, high = get_range_limits(subset['test_range_info'].iloc[0])
        if len(ranges) > 1:
            low = None
            high = None
            print(f"Ranges Discrepancy: [{distinct_range}]")
            note_color = 'red'
            note_text += "\n** DISCREPANCY\nAT SOURCE\nReview Manually"

        if low is not None and high is not None:
            # Identify points outside the range
            outliers = subset[(subset['value'] < low) | (subset['value'] > high)]
            
            if not outliers.empty:
                # Overlay RED dots on top of the blue ones for outliers
                # zorder=2 ensures they sit on top of the line
                ax.scatter(outliers['when_date'], outliers['value'], 
                           color='red', edgecolors='black', s=50, label='Out of Range', zorder=2)
                print(f"Plotted [{len(outliers)}] outliers red.")
                note_text += f"\n{len(outliers)} outliers"
                note_color = 'red'
        
        ax.text(1.02, 0.5, note_text, 
                transform=ax.transAxes, 
                ha='left', va='center', 
                fontsize=8, color=note_color, 
                style='italic', wrap=True)
    
        ax.set_ylabel("Value")
        ax.set_title(f"Test: {code}", loc='left', fontsize=12, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.7)

    axes[-1].set_xlabel("Date")
    # note: extra formatting here removed in favour us simply adding them after the fact graphically

    # Save and Close
    plt.savefig(output_file, bbox_inches='tight')
    plt.close(fig) # CRITICAL: Closes the figure to free up memory
    #print(f"{num_plots} plot(s) [{ header_info if header_info else output_file}] saved to a single file: {os.path.basename(output_file)}")
    print(f"{num_plots} plot(s) [{output_file}] saved to a single file: {os.path.basename(output_file)}")

def get_user_selection(groups_list):
    print("\n--- Available Groups ---")
    for i, name in enumerate(groups_list, 1):
        print(f"[{i}] {name}")
    
    prompt = "\nRun all? [ENTER] | Specific? (e.g. 1,3) | [Q]uit: "
    user_input = input(prompt).strip().lower()

    # 1. Handle Quit
    if user_input == 'q':
        print("Exiting. No changes made.")
        exit()

    # 2. Handle "Run All"
    if user_input == "":
        return groups_list

    # 3. Handle specific numbers
    selected = []
    # Split by comma and look at each piece
    for part in user_input.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            # Check if the number is actually in our list range
            if 0 <= idx < len(groups_list):
                selected.append(groups_list[idx])
    
    return selected

def backup_file(original_path):
    path = Path(original_path)
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    backup_path = path.with_suffix(f".{timestamp}.bk")   
    shutil.copy2(path, backup_path)
    print(f"**** Backup created: {backup_path}")
    return backup_path

# Import function for special json (Sask Health Lab Data circa 2026)
def import_lab_json(raw_json: str) -> List[LabResult]:
    data = json.loads(raw_json, strict=False)
    flattened_list = []

    for entry in data:
        for group in entry.get("group", []):
            group_name = group.get("groupName", "Unknown Group")
            for res in group.get("results", []):
                vals = res.get("values", {})
                raw_val = vals.get("value")
                if raw_val is None or str(raw_val).strip().upper() == "NO VALUE":
                    clean_val = float('nan')
                else:
                    try:
                        clean_val = float(raw_val)
                    except (ValueError, TypeError):
                        clean_val = -10000.0
                
                # the main record
                lab_obj = LabResult(
                    grouping        = group_name,
                    test_name       = res.get("clinicalCode", {}).get("text", "No Code"), # note: this should default to the group name if nothing is here
                    value           = clean_val,
                    when_date       = parse_date(res.get("whenDate"), None),  #should fail
                    is_in_range     = vals.get("isValueInRange", True),
                    test_range_info = vals.get("rangeDisplayText", ""),
                    test_note       = res.get("note", "")
                )
                flattened_list.append(lab_obj)

    return flattened_list

# --- MAIN ---
if __name__ == "__main__":        
    try:
        # ======================================================       
        # Big start
        print(f"Starting HealthLabResults", end="" )

        # output folder based on time
        timestamp = datetime.now().strftime("%Y.%m.%d.%H%M.%S") # for testing
        run_folder = Path(f"lab_results.{timestamp}")
        run_folder.mkdir(parents=True, exist_ok=True)       
        print(f"Created run folder: {run_folder}")
            
        if len(sys.argv) != 3:
            print("\n===== OOPSY! Wrong amount of parameters! ======\n\nUsage: poetry run python3 HealthLabResults.py data.json reference.tsv\n")
            sys.exit(1)
     
        # Basic parameter and file existence checks 
        input_file     = sys.argv[1]
        input_file_path = Path(input_file)
        if not input_file_path.is_file():
            print(f"Error: The file '{input_file}' was not found in {Path.cwd()}")
            sys.exit(1)
        print(f" Input[{input_file}]", end="")
     
        reference_file = sys.argv[2]
        reference_file_path = Path(reference_file)
        if not reference_file_path.is_file():
            print(f"Error: The file '{reference_file}' was not found in {Path.cwd()}")
            sys.exit(1)
        print(f" Reference[{reference_file_path}]\n")
     
        # ---- importing ----
        # the raw json that is all the lab results
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            main_data = import_lab_json(raw_content)
            
            print(f"--- Successfully imported {len(main_data)} records from {input_file} ---")

            # Debug Leftover:
            # print(f"\nA quick sample:")        
            # # Print a quick sample to verify
            # for i, item in enumerate(my_table[:3]):
            #     print(f"{i}: {item.grouping} | {item.when_date} | {item.test_name} | {item.value} | {item.test_range_info} | {item.is_in_range} ")
     
        except Exception as e:
            print(f"Data Importing Error: {e}")        
     
        # Reference file that helps bucket testing, give title and adds clinical use for footer
        try:
            ref_datax = pd.read_csv(
                reference_file_path, 
                sep = '\t', 
                dtype = {
                    'data_test_name'         : str,
                    'functional_equivalent'  : str,
                    'test_name'              : str,
                    'safe_filename'          : str,
                    'test_abbreviation'      : str,
                    'common_clinical_uses'   : str,
                    'typical_reference_range': str
                }
            )
            
            ref_data = [RefEntry(**row) for row in ref_datax.to_dict('records')]
            print(f"--- Successfully imported {len(ref_data)} records from {reference_file} ---")
     
            # Debug leftover:
            # print(f"\nA quick sample:")        
            # # Print a quick sample to verify
            # for i, item in enumerate(ref_data[:3]):
            #     print(f"{i}: {item}") # | {item.when_date} | {item.test_name} | {item.value} | {item.test_range_info} | {item.is_in_range} ")
     
        except Exception as e:
            print(f"Data Importing Error: {e}")        
     
        # validation - are all lab results in the input existing in the reference?  Warn and give options
        main_test_names = set(item.grouping for item in main_data)
        ref_test_names = set(ref.data_test_name for ref in ref_data)
        missing_test_names = main_test_names - ref_test_names
        if missing_test_names:
            print(f"Oops! {len(missing_test_names)} test names missing from reference.")
            for i, test_name in enumerate(sorted(missing_test_names)):
                print(f"{test_name}")
            while True:
                choice = input("Select: [Q] Quit, [A] Add with default values, [I] Process without the missing reference test(s)   Your Answer: ").strip()
                
                if choice.upper() == "Q":
                    print("Exiting to fix reference file. Goodbye!")
                    exit() # Stops the whole script
                    
                elif choice.upper() == "A":
                    print(f"Adding references file with defaults...")
                    backup_file(reference_file_path)
                    for i, test_name in enumerate(sorted(missing_test_names)):
                        hex_code = secrets.token_hex(3)
                        clean_name = "".join(char for char in test_name if char.isalnum())                    
                        new_row = {
                            'data_test_name'         : test_name,
                            'functional_equivalent'  : test_name,
                            'test_name'              : test_name,
                            'safe_filename'          : f"{clean_name[0:5]}{hex_code}",
                            'test_abbreviation'      : clean_name[0:5],
                            'common_clinical_uses'   : "TBA",
                            'typical_reference_range': "TBA"
                        }
                        print(f"Added: {test_name} with same outputname {clean_name[0:5]}{hex_code}")
                        ref_datax = pd.concat([ref_datax, pd.DataFrame([new_row])], ignore_index=True)
                        # so you can process it immediately following..
                        ref_test_names.add(test_name) 
                        main_test_names.add(test_name)
                                                
                    ref_datax.to_csv(reference_file_path, sep='\t', index=False)
                    ref_data = [RefEntry(**row) for row in ref_datax.to_dict('records')] # so you can process them immediately
                    print(f"Done adding - proceeding.. (you should really quit and fill in the other information - makes the charts better)")
     
                    # Logic to add to your ref_data list goes here
                    break # Move to the next anomaly
                    
                elif choice.upper() == "I":
                    print(f"Ignoring for this session.")
                    break # Move to the next anomaly
                    
                else:
                    print("❌ Invalid input. Please type Q, A, or I ")
     
        actionable_test_names = main_test_names & ref_test_names
        print(f"Export Data and Chart these Tests from the provided data:")
        for i,test_name in enumerate(sorted(actionable_test_names)):
            print(f"{i}: {test_name}")
        print(f"Run them all?  [ENTER] to proceed, Q to Quit or type the numbers separated by commas (ie 1,6,9) and [ENTER]")

        # ===========================================================
        # we are on our way - let's get our choices and move forward
     
        actioning_choices = get_user_selection(sorted(list(actionable_test_names)))
        
        if not actioning_choices:
            print("No valid groups selected. Sorry you're having trouble. Exiting - no changes made.")
            exit() # fast exit
        else:
            if (len(actioning_choices) == len(actionable_test_names)):
                print(f"\nReady to process ALL?")
            else:
                print(f"\nReady to process: {' | '.join(actioning_choices)}")
     
            confirm = input("Proceed? [ENTER] and Y proceed, 'n' Cancels: ").strip().lower()
            
            if confirm in ['', 'y', 'yes']:
                print("Starting the run...")                
            else:
                print("Cancelled by user.")               
                exit() # fast exit
       
        unique_functional_groups = sorted(list(set(
            ref.functional_equivalent 
            for ref in ref_data 
            if ref.data_test_name in actioning_choices
        )))
        for functional_group in unique_functional_groups:
            # the canonical record (aka functional group - aka "bucket") ie all PSA tests go in one like a panel group
            cannonical_record = [r for r in ref_data if r.data_test_name == functional_group][0]        
            these_data_test_names = sorted(list(set(ref.data_test_name for ref in ref_data if ref.functional_equivalent == functional_group)))
            this_dump_base_path = run_folder / f"{cannonical_record.safe_filename}"
            this_dump_tsv_path = f"{this_dump_base_path}.tsv"
            this_dump_png_path = f"{this_dump_base_path}.png"
            accumulator = []
            name_accumulator = ""
            print(f"\nStarting Data Dump and Plot for [{cannonical_record.test_name}]")
            for this_data_test_name in these_data_test_names:
                this_data_test_records = [lab for lab in main_data if lab.grouping == this_data_test_name]
                accumulator.extend(this_data_test_records)
                name_accumulator += "| " + this_data_test_name
            if accumulator:
                this_dump = pd.DataFrame([lab.model_dump() for lab in accumulator])
                this_dump.to_csv(this_dump_tsv_path, sep="\t", index=False)
                print(f"TSV save complete: {len(accumulator)} records saved. {name_accumulator} |")
                generate_health_plot( this_dump_tsv_path, this_dump_png_path)                
                plot_title = format_title(cannonical_record.test_name, f"{cannonical_record.test_abbreviation}")
                # TODO: add other nice things like printed date, patient name/initials etc...
                add_branding_to_png(this_dump_png_path, plot_title, f"Clinical use: Rule out {cannonical_record.common_clinical_uses}")
            else:
                print(f"That's Odd - nothing for [{cannonical_record.functional_equivalent}].")
    except Exception as e:
        print(f" Script Crashed: {e}", exc_info=true)

print(f"\nEverything has been logged to {run_folder}/output.log") 
# completely optional stuff for tidying up log file
cleanup_file = "cleanup.txt"
with open(cleanup_file, "w") as f:    
    f.write(f"cp output.log {run_folder}/;gio trash {cleanup_file};gio trash output.log")

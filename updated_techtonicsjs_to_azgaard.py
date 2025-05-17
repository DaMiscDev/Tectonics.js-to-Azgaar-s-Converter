import tkinter as tk
from tkinter import filedialog
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

a = 1

# === SETTINGS ===
cell_width = a     # Keep small for grid accuracy
cell_height = a
x_min, x_max = -180, 180
y_min, y_max = -90, 90

# === ELEVATION CLASSIFICATION FUNCTION ===
def classify_elevation(elevation):
    try:
        elevation = float(elevation)
        thresholds = [
            (-3248, 0), (-3117, 1), (-1476, 2), (-930, 3), (-656, 4),
            (-492, 5), (-383, 6), (-305, 7), (-246, 8), (-201, 9),
            (-164, 10), (-134, 11), (-109, 12), (-88, 13), (-70, 14),
            (-55, 15), (-41, 16), (-29, 17), (-18, 18), (-9, 19),
            (13, 20), (30, 21), (52, 22), (82, 23), (118, 24),
            (161, 25), (210, 26), (266, 27), (328, 28), (347, 29),
            (472, 30), (554, 31), (643, 32), (738, 33), (840, 34),
            (948, 35), (1063, 36), (1184, 37), (1312, 38), (1447, 39),
            (1588, 40), (1736, 41), (1890, 42), (2051, 43), (2218, 44),
            (2392, 45), (2572, 46), (2759, 47), (2953, 48), (3153, 49),
            (3360, 50), (3573, 51), (3793, 52), (4019, 53), (4252, 54),
            (4492, 55), (4738, 56), (4990, 57), (5250, 58), (5515, 59),
            (5788, 60), (6067, 61), (6352, 62), (6644, 63), (6943, 64),
            (7248, 65), (7559, 66), (7878, 67), (8203, 68), (8534, 69),
            (8872, 70), (9216, 71), (9567, 72), (9925, 73), (10289, 74),
            (10660, 75), (11037, 76), (11421, 77), (11812, 78), (12209, 79),
            (12612, 80), (13022, 81), (13439, 82), (13862, 83), (14292, 84),
            (14728, 85), (15171, 86), (15621, 87), (16077, 88), (16540, 89),
            (17009, 90), (17484, 91), (17967, 92), (18456, 93), (18951, 94),
            (19453, 95), (19962, 96), (20477, 97), (20998, 98), (21527, 99)
        ]
        for threshold, category in thresholds:
            if elevation <= threshold:
                return category
        return 100
    except ValueError:
        return None

# === PLOT FUNCTION ===
def plot_grid(df, output_path='elevation_grid.png'):
    # Round coordinates to int for plotting on a grid
    df['lon_int'] = df['longitude(degrees)'].round().astype(int)
    df['lat_int'] = df['latitude (degrees)'].round().astype(int)

    # Build a dict using rounded coords
    elevation_dict = {(row['lon_int'], row['lat_int']): row['Category'] for _, row in df.iterrows()}

    fig, ax = plt.subplots(figsize=(12, 6))

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            category = elevation_dict.get((x, y), None)

            if category is None:
                color = "black"  # No data
            else:
                # Normalize to range 0.0 (black) to 1.0 (white)
                norm_value = max(0, min(100, category)) / 100.0
                color = str(norm_value)  # Grayscale

            rect = patches.Rectangle((x, y), cell_width, cell_height, linewidth=0, edgecolor=None, facecolor=color)
            ax.add_patch(rect)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.show()

def fill_missing_cells(df):
    df['lon_int'] = df['longitude(degrees)'].astype(int)
    df['lat_int'] = df['latitude (degrees)'].astype(int)
    elev_lookup = {(row['lon_int'], row['lat_int']): row['elevation (ft)'] for _, row in df.iterrows()}

    added_rows = []

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if (x, y) in elev_lookup:
                continue

            neighbors = [
                (x-1, y+1), (x, y+1), (x+1, y+1),
                (x-1, y),             (x+1, y),
                (x-1, y-1), (x, y-1), (x+1, y-1)
            ]
            values = [elev_lookup.get(coord) for coord in neighbors]
            values = [v for v in values if pd.notna(v)]

            if len(values) >= 3:
                avg_elev = sum(values) / len(values)
                new_row = {
                    'longitude(degrees)': x,
                    'latitude (degrees)': y,
                    'elevation (ft)': avg_elev,
                    'Category': classify_elevation(avg_elev)
                }
                elev_lookup[(x, y)] = avg_elev
                added_rows.append(new_row)

    if added_rows:
        df = pd.concat([df, pd.DataFrame(added_rows)], ignore_index=True)

    return df, len(added_rows)

def fill_internal_land_holes(df):
    # Snap coords to ints
    df['lon_int'] = df['longitude(degrees)'].round().astype(int)
    df['lat_int'] = df['latitude (degrees)'].round().astype(int)

    # Build a dict for constant-time scalar lookups
    elev_lookup = {
        (row['lon_int'], row['lat_int']): row['elevation (ft)']
        for _, row in df.iterrows()
    }

    new_rows = []

    # Iterate the full integer grid
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            elev = elev_lookup.get((x, y), None)

            # Skip if already positive land
            if elev is not None and elev > 0:
                continue

            # Check the 4 cardinal neighbors are all > 0
            cardinals = [(x, y+1), (x+1, y), (x, y-1), (x-1, y)]
            if any(elev_lookup.get(c) is None or elev_lookup[c] <= 0 for c in cardinals):
                continue

            # Collect all 8 neighbor elevations that exist
            all_nbrs = [
                (x+dx, y+dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if not (dx == 0 and dy == 0)
            ]
            vals = [elev_lookup[c] for c in all_nbrs if elev_lookup.get(c) is not None]

            if not vals:
                continue

            # Make a new filled cell
            avg_elev = sum(vals) / len(vals)
            new_rows.append({
                'longitude(degrees)': x,
                'latitude (degrees)': y,
                'elevation (ft)': avg_elev,
                'Category': classify_elevation(avg_elev)
            })
            # Update lookup so later passes see it
            elev_lookup[(x, y)] = avg_elev

    # Append any new rows to df
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    return df, len(new_rows)

# === MAIN FILE HANDLER ===
def handle_file():
    filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not filepath:
        return

    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    # Convert elevation from meters to feet if needed
    if 'elevation (m)' in df.columns:
        df['elevation (m)'] = pd.to_numeric(df['elevation (m)'], errors='coerce')
        df['elevation (ft)'] = df['elevation (m)'] * 3.28084
        print("Converted elevation from meters to feet.")
    elif 'elevation (ft)' not in df.columns:
        print("Missing both 'elevation (m)' and 'elevation (ft)' columns. Cannot proceed.")
        return

    # Apply classification
    df['Category'] = df['elevation (ft)'].apply(classify_elevation)

    # Fill outer grid gaps
    total_filled = 0
    while True:
        df, filled = fill_missing_cells(df)
        total_filled += filled
        print(f"Filled {filled} new points...")
        if filled == 0:
            break
    print(f"Total filled points: {total_filled}")

    # Fill internal land holes until no more are found
    total_holes_filled = 0
    while True:
        df, holes_filled = fill_internal_land_holes(df)
        total_holes_filled += holes_filled
        print(f"Internal holes filled this round: {holes_filled}")
        if holes_filled == 0:
            break
    print(f"Total internal holes filled: {total_holes_filled}")

    # Fill holes inside landmasses (all 8 neighbors > 0)
    df, _ = fill_internal_land_holes(df)

    # Save updated CSV
    new_csv_path = os.path.splitext(filepath)[0] + '_updated.csv'
    df.to_csv(new_csv_path, index=False)
    print(f"Updated CSV saved to: {new_csv_path}")
    print(df.head())

    # Plot elevation grid
    plot_grid(df)


# === TKINTER UI ===
window = tk.Tk()
window.title("CSV Elevation Classifier & Plotter")

upload_btn = tk.Button(window, text="Upload CSV and Run", command=handle_file)
upload_btn.pack(pady=20)

window.mainloop()

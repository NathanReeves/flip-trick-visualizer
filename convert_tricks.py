import csv
import json

### Converts a rough trick_names.csv file into a more refined TrickCatalog.json file.


# Input and output filenames
INPUT_FILENAME = "trick_names.csv"
OUTPUT_FILENAME = "TrickCatalog.json"

def extract_other_names(trick_name):
    """Extract alternative names from parentheses in the trick name."""
    if '(' not in trick_name:
        return []
    
    # Extract content between parentheses
    other_names_str = trick_name[trick_name.find('(') + 1:trick_name.find(')')].strip()
    
    # Return empty list if the parentheses contain an asterisk
    if '*' in other_names_str:
        return []

    # Split by '+' or ',' and clean up each name
    other_names = [name.strip() for name in other_names_str.split(',')]
    return other_names

def create_trick_entry(spin, flip, body, active_stance, name):
    """Create a trick entry with trick name and other names."""
    # Remove other names in parentheses from trick name
    trick_name = name.split('(')[0].strip()
    
    return {
        "compositeKey": f"S{spin},F{flip},B{body},A{active_stance}",
        "trickName": trick_name,
        "parameters": {
            "spin": int(spin),
            "flip": int(flip),
            "body": int(body),
            "activeStance": int(active_stance)
        },
        "otherNames": extract_other_names(name)
    }

def csv_to_trick_catalog(input_file, output_file):
    tricks = []

    # Open the CSV file and filter out comment lines and empty lines.
    with open(input_file, "r", newline="") as csvfile:
        # Filter lines: skip comments (lines starting with '#') and empty lines.
        filtered_lines = filter(lambda line: line.strip() and not line.strip().startswith("#"), csvfile)
        reader = csv.reader(filtered_lines)
        for row in reader:
            # Ensure we have at least five columns: spin, flip, body, activeStance, trickName
            if len(row) < 5:
                continue

            try:
                spin = int(row[0])
                flip = int(row[1])
                body = int(row[2])
                active_stance = int(row[3])
            except ValueError:
                # Skip rows with invalid numeric parameters.
                continue

            name = row[4].strip()
            # Use the create_trick_entry function instead of manual dictionary creation
            trick = create_trick_entry(spin, flip, body, active_stance, name)
            tricks.append(trick)

    # Create the final JSON structure with a version and a list of tricks.
    output_data = {
        "version": "1.0",
        "tricks": tricks
    }

    # Write the JSON output with indentation for readability.
    with open(output_file, "w") as jsonfile:
        json.dump(output_data, jsonfile, indent=4)
    print(f"Successfully wrote {len(tricks)} tricks to {output_file}.")

if __name__ == "__main__":
    csv_to_trick_catalog(INPUT_FILENAME, OUTPUT_FILENAME)

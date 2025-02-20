import json

# Assume our trick catalog JSON has been loaded and has the structure:
# {
#   "version": "1.0",
#   "tricks": [
#       {
#         "compositeKey": "S0,F0,B0",
#         "canonicalName": "Ollie",
#         "parameters": { "spin": 0, "flip": 0, "body": 0 },
#         "variant": "none",
#         "otherNames": []
#       },
#       {
#         "compositeKey": "S180,F-360,B0",
#         "canonicalName": "Varial Heelflip",
#         "parameters": { "spin": 180, "flip": -360, "body": 0 },
#         "variant": "none",
#         "otherNames": []
#       },
#       {
#         "compositeKey": "S-360,F0,B0",
#         "canonicalName": "FS Shuv",
#         "parameters": { "spin": -360, "flip": 0, "body": 0 },
#         "variant": "none",
#         "otherNames": []
#       }
#       // ... other tricks
#   ]
# }

def load_trick_catalog(filename="TrickCatalog.json"):
    with open(filename, "r") as f:
        data = json.load(f)
    # Build a dictionary keyed by compositeKey for fast lookup.
    catalog = { trick["compositeKey"]: trick for trick in data.get("tricks", []) }
    return catalog

def normalize_parameters(spin, flip, body, natural_stance, active_stance):
    """
    Applies inversion factors based on stances:
    - If NaturalStance is 'Regular', invert the parameters.
    - If ActiveStance is 'Switch', invert them as well.
    If both are true, the inversions cancel out.
    """
    factor = 1
    if natural_stance.lower() == "regular":
        factor *= -1
    if active_stance.lower() == "switch":
        factor *= -1
    return factor * spin, factor * flip, factor * body

def process_trick(input_data, catalog):
    # Extract base parameters.
    base_spin      = input_data.get("Spin")
    base_flip      = input_data.get("Flip")
    base_body      = input_data.get("Body")
    natural_stance = input_data.get("NaturalStance", "Regular")
    active_stance  = input_data.get("ActiveStance", "")

    # Normalize base trick parameters.
    norm_spin, norm_flip, norm_body = normalize_parameters(
        base_spin, base_flip, base_body, natural_stance, active_stance
    )
    base_key = f"S{norm_spin},F{norm_flip},B{norm_body}"
    base_trick = catalog.get(base_key)
    base_name = base_trick["canonicalName"] if base_trick else "Unknown Trick"

    # Build the result with active stance as a prefix.
    result = base_name
    if active_stance.lower() != "normal":
        result = f"{active_stance} {base_name}"
    result = result.strip()

    # Initialize output dictionary with trickName
    output = {"trickName": result}
    
    # Add otherNames if they exist
    if base_trick and base_trick.get("otherNames"):
        output["otherNames"] = base_trick["otherNames"]

    # If LateParams are provided, process them similarly.
    late_params = input_data.get("LateParams")
    if late_params:
        late_spin = late_params.get("Spin")
        late_flip = late_params.get("Flip")
        late_body = late_params.get("Body")
        norm_late_spin, norm_late_flip, norm_late_body = normalize_parameters(
            late_spin, late_flip, late_body, natural_stance, active_stance
        )
        late_key = f"S{norm_late_spin},F{norm_late_flip},B{norm_late_body}"
        late_trick = catalog.get(late_key)
        late_name = late_trick["canonicalName"] if late_trick else "Unknown Late Trick"
        output["trickName"] += f" Late {late_name}"
        output["lateTrickName"] = late_name  # Add separate lateTrickName field
        
        # Add late trick otherNames if they exist
        if late_trick and late_trick.get("otherNames"):
            output["lateTrickOtherNames"] = late_trick["otherNames"]

    return output

# Example usage:
if __name__ == "__main__":
    catalog = load_trick_catalog("TrickCatalog.json")

    input = {
        "Spin": -180,
        "Flip": 360,
        "Body": 0,
        "NaturalStance": "Regular",
        "ActiveStance": "Fakie"
    }
    output = process_trick(input, catalog)
    print(output)  # Expected: {"result": "Fakie Varial Heelflip"} 

    # Example with a late-flip:
    input_with_late = {
        "Spin": -180,
        "Flip": 360,
        "Body": 0,
        "NaturalStance": "Regular",
        "ActiveStance": "Fakie",
        "LateParams": {"Spin": -360, "Flip": 0, "Body": 0}
    }
    output2 = process_trick(input_with_late, catalog)
    print(output2)  # Expected: {"result": "Fakie Varial Heelflip Late Frontside 360 Shuv"}

